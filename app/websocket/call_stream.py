"""
SatyaSwar - Call Audio Streaming WebSocket Handler
Member 2: Backend, Infrastructure, Database and Security

Handles real-time bi-directional audio streaming, frame validation, backpressure
management, ML inference dispatching, and live risk broadcasting for call sessions.
Implements bounded queue draining on clean termination, single-execution finalization,
and resilient failure handling.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.decision.risk_engine import (
    RiskState,
    classify_risk,
    compute_final_outcome,
    evaluate_decision,
    update_risk_state,
)
from app.dependencies.auth import (
    WS_AUTH_FAILED_CODE,
    authenticate_websocket,
)
from app.models.enums import (
    ActionType,
    EvidenceQualityLevel,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.repositories import calls as calls_repo
from app.repositories import verification as verification_repo
from app.services.ml_service import MLClient, MLUnavailable
from app.websocket.audio_frame import (
    InvalidAudioFrameError,
    parse_audio_frame,
)
from app.websocket.connection import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Call Streaming"])

# Custom WebSocket close codes (RFC 6455 4000-4999 application range)
WS_FORBIDDEN_CODE = 4403
WS_SESSION_NOT_FOUND_CODE = 4404
WS_SESSION_CONFLICT_CODE = 4409
WS_INVALID_FRAME_CODE = 4413
WS_RATE_EXCEEDED_CODE = 4429
WS_HEARTBEAT_TIMEOUT_CODE = 4408

HEARTBEAT_TIMEOUT_SECONDS = 30.0
MAX_QUEUE_SIZE = 4
DRAIN_TIMEOUT_SECONDS = 10.0

# Sentinel indicating end-of-audio stream for clean worker queue draining
SENTINEL_STOP = object()


async def handle_call_stream(websocket: WebSocket, session_id: str) -> None:
    """
    Main WebSocket streaming lifecycle handler for a call session.
    """
    # Step 1: Authenticate connection (supports both Authorization header & first-message auth)
    try:
        user = await authenticate_websocket(websocket)
    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.warning("WebSocket authentication error for session %s: %s", session_id, e)
        try:
            await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Authentication failed")
        except Exception:
            pass
        return

    # Step 2: Validate session ownership & state
    try:
        session = calls_repo.get_owned_session(session_id, user.uid)
    except Exception:
        logger.warning("Session %s not found or access denied for user %s", session_id, user.uid)
        await websocket.close(code=WS_SESSION_NOT_FOUND_CODE, reason="Call session not found")
        raise WebSocketDisconnect(code=WS_SESSION_NOT_FOUND_CODE)

    if session.status not in (SessionStatus.CREATED, SessionStatus.ACTIVE):
        logger.warning("Session %s in invalid status %s for streaming", session_id, session.status.value)
        await websocket.close(
            code=WS_SESSION_CONFLICT_CODE,
            reason=f"Session is already in terminal state: {session.status.value}",
        )
        raise WebSocketDisconnect(code=WS_SESSION_CONFLICT_CODE)

    # Step 3: Transition CREATED -> ACTIVE
    if session.status == SessionStatus.CREATED:
        try:
            calls_repo.transition_session_status(
                session_id=session_id,
                user_id=user.uid,
                new_status=SessionStatus.ACTIVE,
                allowed_from={SessionStatus.CREATED},
            )
        except Exception as e:
            logger.warning("Failed to transition session %s to ACTIVE: %s", session_id, e)

    # Register socket with connection manager
    manager.add(session_id, websocket)

    # Send connection_ready acknowledgement
    ready_event = {
        "type": "connection_ready",
        "session_id": session_id,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "config": {
            "windowMs": 3500,
            "hopMs": 1750,
            "sampleRate": 16000,
        },
    }
    await websocket.send_json(ready_event)

    # Step 4: Per-session state & worker queues
    risk_state = RiskState()
    last_seq: Optional[int] = None
    audio_queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    ml_client = MLClient()
    last_activity_time = time.time()

    # Lifecycle coordination flags
    stop_receiving = asyncio.Event()
    finalized = False
    worker_failed = False

    async def receiver_task():
        nonlocal last_seq, last_activity_time
        try:
            while not stop_receiving.is_set():
                message = await websocket.receive()
                last_activity_time = time.time()

                # Handle client close / disconnect
                if message["type"] == "websocket.disconnect":
                    logger.info("Client disconnected in session %s", session_id)
                    stop_receiving.set()
                    await audio_queue.put(SENTINEL_STOP)
                    break

                # Handle binary audio frame
                if "bytes" in message and message["bytes"]:
                    if stop_receiving.is_set():
                        continue

                    raw_bytes = message["bytes"]
                    try:
                        frame = parse_audio_frame(raw_bytes, last_seq=last_seq)
                        last_seq = frame.seq
                    except InvalidAudioFrameError as exc:
                        logger.warning("Invalid audio frame in session %s: %s", session_id, exc)
                        await websocket.send_json({
                            "type": "error",
                            "code": "INVALID_AUDIO_FRAME",
                            "message": exc.message,
                            "fatal": False,
                        })
                        continue

                    # Bounded queue backpressure: drop oldest if queue is full (never drop SENTINEL_STOP)
                    if audio_queue.full():
                        try:
                            dropped = audio_queue.get_nowait()
                            if dropped is SENTINEL_STOP:
                                await audio_queue.put(SENTINEL_STOP)
                            else:
                                audio_queue.task_done()
                                logger.warning(
                                    "Backpressure: dropped oldest audio window in session %s",
                                    session_id,
                                )
                        except asyncio.QueueEmpty:
                            pass

                    await audio_queue.put(frame)

                    if frame.is_last:
                        logger.info("Received final audio window (is_last=True) for session %s", session_id)
                        stop_receiving.set()
                        await audio_queue.put(SENTINEL_STOP)
                        break

                # Handle text control messages
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type")
                    if msg_type == "hello":
                        await websocket.send_json({
                            "type": "hello_ack",
                            "callId": session_id,
                            "config": {"windowMs": 3500, "hopMs": 1750},
                        })
                    elif msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "session_id": session_id,
                            "server_time": datetime.now(timezone.utc).isoformat(),
                        })
                    elif msg_type == "end":
                        logger.info("Client requested end of call for session %s", session_id)
                        stop_receiving.set()
                        await audio_queue.put(SENTINEL_STOP)
                        break

        except WebSocketDisconnect:
            stop_receiving.set()
            try:
                await audio_queue.put(SENTINEL_STOP)
            except Exception:
                pass
        except Exception as e:
            logger.error("Error in receiver task for session %s: %s", session_id, e)
            stop_receiving.set()
            try:
                await audio_queue.put(SENTINEL_STOP)
            except Exception:
                pass

    async def ml_worker_task():
        nonlocal risk_state, worker_failed
        consecutive_ml_failures = 0
        try:
            while True:
                item = await audio_queue.get()
                if item is SENTINEL_STOP:
                    audio_queue.task_done()
                    logger.info("ML worker reached SENTINEL_STOP for session %s", session_id)
                    break

                frame = item
                try:
                    t_start = time.perf_counter()
                    ml_result = await ml_client.score_window(
                        session_id=session_id,
                        window_id=frame.seq,
                        pcm_bytes=frame.pcm_bytes,
                    )
                    processing_ms = int((time.perf_counter() - t_start) * 1000)

                    consecutive_ml_failures = 0
                    spoof_score = float(ml_result["spoof_score"])
                    evidence_quality = float(ml_result["evidence_quality"])

                    update_risk_state(risk_state, spoof_score, evidence_quality)
                    classification = classify_risk(risk_state, ml_available=True)

                    # Update live metrics in Firestore
                    try:
                        calls_repo.update_session_live_risk(
                            session_id=session_id,
                            user_id=user.uid,
                            risk_score=classification["risk_score"] or 0.0,
                            risk_level=classification["risk_level"],
                            evidence_quality=classification["evidence_quality"],
                            window_count=risk_state.windows_total,
                        )
                    except Exception as e:
                        logger.warning("Failed to update live risk in Firestore: %s", e)

                    # Broadcast standard risk update
                    score_message = {
                        "type": "score",
                        "seq": frame.seq,
                        "windowStartMs": frame.offset_ms,
                        "windowRiskIndex": int(round(spoof_score * 100)),
                        "call": {
                            "riskIndex": int(round((risk_state.rolling_score or 0.0) * 100)),
                            "band": classification["risk_level"].value.lower(),
                            "peakRiskIndex": int(round((risk_state.peak_risk or 0.0) * 100)),
                        },
                        "voiceOutcome": classification["voice_outcome"],
                        "evidence": {
                            "level": classification["evidence_quality"].value,
                            "usableSpeechSec": round(risk_state.windows_good * 1.75, 2),
                        },
                        "serverProcessingMs": processing_ms,
                    }
                    await manager.broadcast(session_id, score_message)

                except MLUnavailable as exc:
                    consecutive_ml_failures += 1
                    logger.warning("ML inference failure (#%d) for session %s: %s", consecutive_ml_failures, session_id, exc)
                    if consecutive_ml_failures >= 3:
                        await manager.broadcast(session_id, {
                            "type": "analysis_unavailable",
                            "code": "ML_SERVICE_UNAVAILABLE",
                            "message": "Analysis temporarily unavailable due to upstream model timeout",
                        })
                finally:
                    audio_queue.task_done()

        except asyncio.CancelledError:
            logger.info("ML worker task cancelled for session %s", session_id)
            raise
        except Exception as e:
            logger.error("Fatal error in ML worker task for session %s: %s", session_id, e)
            worker_failed = True

    async def heartbeat_task():
        try:
            while not stop_receiving.is_set():
                await asyncio.sleep(2.0)
                if time.time() - last_activity_time > HEARTBEAT_TIMEOUT_SECONDS:
                    logger.warning(
                        "Session %s exceeded heartbeat timeout (%.1fs)",
                        session_id,
                        HEARTBEAT_TIMEOUT_SECONDS,
                    )
                    await manager.broadcast(session_id, {
                        "type": "error",
                        "code": "HEARTBEAT_TIMEOUT",
                        "message": "Connection timed out due to inactivity",
                        "fatal": True,
                    })
                    stop_receiving.set()
                    try:
                        await audio_queue.put(SENTINEL_STOP)
                    except Exception:
                        pass
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.close(code=WS_HEARTBEAT_TIMEOUT_CODE, reason="Heartbeat timeout")
                    break
        except asyncio.CancelledError:
            pass

    async def finalize_session():
        nonlocal finalized
        if finalized:
            return
        finalized = True

        # Fetch authoritative verification and session state from server-side database
        try:
            current_session = calls_repo.get_owned_session(session_id, user.uid)
        except Exception:
            current_session = None

        ver_req = verification_repo.get_latest_verification_for_session(session_id)

        if ver_req is not None:
            v_status = ver_req.status
            act_type = ver_req.action_type
        elif current_session is not None:
            v_status = current_session.verification_status
            act_type = getattr(current_session, "action_type", ActionType.OTHER)
        else:
            v_status = VerificationStatus.NOT_REQUESTED
            act_type = ActionType.OTHER

        # If worker failed fatally or ML failed consecutively, analysis is marked unavailable
        ml_available = not worker_failed and (risk_state.ml_failures_in_row < 3)

        decision = evaluate_decision(
            state=risk_state,
            verification_status=v_status,
            action_type=act_type,
            ml_available=ml_available,
        )
        final_outcome = decision.final_outcome

        outcome_message = {
            "type": "outcome",
            "finalOutcome": final_outcome.value,
            "headline": decision.headline,
            "recommendation": decision.recommendation,
            "shouldHoldAction": decision.should_hold_action,
            "verificationStatus": v_status.value,
            "actionType": act_type.value,
            "peakRiskIndex": int(round((risk_state.peak_risk or 0.0) * 100)),
        }
        await manager.broadcast(session_id, outcome_message)

    # Launch concurrent tasks
    receiver_fut = asyncio.create_task(receiver_task())
    worker_fut = asyncio.create_task(ml_worker_task())
    heartbeat_fut = asyncio.create_task(heartbeat_task())

    try:
        # Wait until receiving stops (normal completion, client disconnect, or heartbeat timeout)
        done, pending = await asyncio.wait(
            [receiver_fut, heartbeat_fut],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel heartbeat watchdog immediately
        if not heartbeat_fut.done():
            heartbeat_fut.cancel()
            try:
                await heartbeat_fut
            except asyncio.CancelledError:
                pass

        # Drain the ML worker queue: allow all queued frames to be processed up to DRAIN_TIMEOUT_SECONDS
        try:
            if not stop_receiving.is_set():
                stop_receiving.set()
                await audio_queue.put(SENTINEL_STOP)

            await asyncio.wait_for(worker_fut, timeout=DRAIN_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("ML worker draining timed out after %.1fs for session %s", DRAIN_TIMEOUT_SECONDS, session_id)
            worker_fut.cancel()
            try:
                await worker_fut
            except (asyncio.CancelledError, Exception):
                pass
        except Exception as e:
            logger.error("Error while awaiting ML worker completion in session %s: %s", session_id, e)

        # Send final outcome before closing socket
        await finalize_session()

    finally:
        # Ensure finalization and cleanup are performed exactly once
        await finalize_session()
        manager.remove(session_id, websocket)
        await ml_client.close()

        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=1000, reason="Call streaming ended")
            except Exception:
                pass


@router.websocket("/ws/v1/calls/{session_id}")
async def call_stream_v1(websocket: WebSocket, session_id: str):
    """Primary WebSocket endpoint for real-time call audio streaming."""
    await handle_call_stream(websocket, session_id)


@router.websocket("/ws/call/{session_id}")
async def call_stream_flutter_alias(websocket: WebSocket, session_id: str):
    """Compatibility alias matching Member 1 Flutter client's proposed WebSocket URL."""
    await handle_call_stream(websocket, session_id)
