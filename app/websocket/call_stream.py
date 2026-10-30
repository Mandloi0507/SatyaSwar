"""
SatyaSwar - Call Audio Streaming WebSocket Handler
Member 2: Backend, Infrastructure, Database and Security

Handles real-time bi-directional audio streaming, frame validation, backpressure
management, ML inference dispatching, and live risk broadcasting for call sessions.
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
    update_risk_state,
)
from app.dependencies.auth import (
    WS_AUTH_FAILED_CODE,
    authenticate_websocket,
)
from app.models.enums import (
    EvidenceQualityLevel,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.repositories import calls as calls_repo
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
    call_ended = asyncio.Event()

    async def receiver_task():
        nonlocal last_seq, last_activity_time
        try:
            while not call_ended.is_set():
                message = await websocket.receive()
                last_activity_time = time.time()

                # Handle client close / disconnect
                if message["type"] == "websocket.disconnect":
                    break

                # Handle binary audio frame
                if "bytes" in message and message["bytes"]:
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

                    # Bounded queue backpressure: drop oldest if queue is full
                    if audio_queue.full():
                        try:
                            _ = audio_queue.get_nowait()
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
                        call_ended.set()
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
                        call_ended.set()
                        break

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("Error in receiver task for session %s: %s", session_id, e)

    async def ml_worker_task():
        nonlocal risk_state
        consecutive_ml_failures = 0
        try:
            while not call_ended.is_set() or not audio_queue.empty():
                try:
                    frame = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

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
            pass
        except Exception as e:
            logger.error("Error in ML worker task for session %s: %s", session_id, e)

    async def heartbeat_task():
        try:
            while not call_ended.is_set():
                await asyncio.sleep(5.0)
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
                    call_ended.set()
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.close(code=WS_HEARTBEAT_TIMEOUT_CODE, reason="Heartbeat timeout")
                    break
        except asyncio.CancelledError:
            pass

    # Run tasks concurrently
    tasks = [
        asyncio.create_task(receiver_task()),
        asyncio.create_task(ml_worker_task()),
        asyncio.create_task(heartbeat_task()),
    ]

    try:
        # Wait until client finishes or disconnects
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

        # Send final outcome before closing if call ended cleanly
        if call_ended.is_set():
            final_outcome = compute_final_outcome(
                risk_state,
                verification_status="NOT_REQUESTED",
                ml_available=True,
            )
            outcome_message = {
                "type": "outcome",
                "finalOutcome": final_outcome.value,
                "headline": (
                    "Likely impersonation detected. Do not proceed."
                    if final_outcome.value == "likely_impersonation"
                    else "Voice analysis completed."
                ),
                "peakRiskIndex": int(round((risk_state.peak_risk or 0.0) * 100)),
            }
            await manager.broadcast(session_id, outcome_message)

    finally:
        # Cleanup connections and clients
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
