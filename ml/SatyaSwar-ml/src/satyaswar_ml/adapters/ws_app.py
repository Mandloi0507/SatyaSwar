"""
FastAPI Standalone Adapter for SatyaSwar ML Service
Authoritative source: Implementation.md, Section 6.1, 6.3, 6.5

Exposes:
- GET  /ml/health
- GET  /ml/model-info
- POST /ml/analyze-window (dev only)
- POST /ml/contacts/match
- WS   /ml/ws/{call_id}
"""

import json
import os
import time

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from satyaswar_ml.adapters.mock import MockCallSession
from satyaswar_ml.config import load_config
from satyaswar_ml.engine import AnalysisEngine, SessionConfig
from satyaswar_ml.nlp.contacts import ContactMatcher
from satyaswar_ml.schemas import (
    ClaimEvent,
    ContactsMatchRequest,
    HealthResponse,
    ModelInfoResponse,
    ScoreEvent,
    SessionStartMessage,
)

app = FastAPI(
    title="SatyaSwar ML Service",
    description="Real-time voice-integrity and voice-cloning impersonation risk ML service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ENGINE: AnalysisEngine | None = None


def get_engine() -> AnalysisEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AnalysisEngine.from_config()
    return _ENGINE


@app.get("/ml/health", response_model=HealthResponse, tags=["Diagnostics"])
async def get_health() -> HealthResponse:
    """Report model loaded status, device, versions, and warm-up latency."""
    cfg = load_config()
    import torch

    import satyaswar_ml

    engine = get_engine()

    return HealthResponse(
        status="ok",
        model_loaded=True,
        device=cfg.detector.device if cfg.detector.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"),
        versions={
            "satyaswar_ml": satyaswar_ml.__version__,
            "torch": torch.__version__,
        },
        warmup_ms=round(engine._warmup_time_ms or 150.0, 1),
        mock=cfg.mock_mode,
    )


@app.get("/ml/model-info", response_model=ModelInfoResponse, tags=["Diagnostics"])
async def get_model_info() -> ModelInfoResponse:
    """Return model name, version, active thresholds, and evaluated languages."""
    cfg = load_config()
    return ModelInfoResponse(
        model_name=cfg.detector.primary,
        version="1.0.0",
        thresholds=cfg.thresholds.model_dump(),
        languages_evaluated=["en", "hi"],
    )


@app.post("/ml/contacts/match", response_model=ClaimEvent, tags=["Matching"])
async def match_contacts(req: ContactsMatchRequest) -> ClaimEvent:
    """Rank user contacts against transcript text (no auto-selection)."""
    matcher = ContactMatcher(req.contacts)
    return matcher.match(req.text)


@app.post("/ml/analyze-window", response_model=ScoreEvent, tags=["Development"])
async def analyze_window(request: Request) -> ScoreEvent:
    """Dev and test only endpoint. Disabled unless ML_ENABLE_DEV_ENDPOINTS=1."""
    if os.getenv("ML_ENABLE_DEV_ENDPOINTS", "0") != "1":
        raise HTTPException(
            status_code=403,
            detail="Dev endpoint /ml/analyze-window is disabled unless ML_ENABLE_DEV_ENDPOINTS=1",
        )
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    engine = get_engine()
    session, _ = engine.start_session(call_id=f"dev_{int(time.time())}")
    events = await session.push_audio(body)
    score_events = [e for e in events if isinstance(e, ScoreEvent)]
    if not score_events:
        raise HTTPException(status_code=400, detail="Audio window could not be scored")
    return score_events[0]


@app.websocket("/ml/ws/{call_id}")
async def websocket_call(websocket: WebSocket, call_id: str):
    """
    Streaming WebSocket endpoint for live call analysis.
    Ingests binary audio frames and outputs JSON event messages.
    """
    await websocket.accept()
    cfg = load_config()
    is_mock = cfg.mock_mode or (os.getenv("ML_MOCK", "0") in ("1", "true", "True"))

    session = None
    engine = None

    if is_mock:
        session = MockCallSession(call_id=call_id)
    else:
        engine = get_engine()

    try:
        while True:
            message = await websocket.receive()
            if message.get("bytes"):
                raw_bytes = message["bytes"]
                if session is None and engine is not None:
                    # Auto-initialize session if client started streaming directly
                    session, ready_ev = engine.start_session(call_id=call_id)
                    await websocket.send_text(ready_ev.model_dump_json())

                if session is not None:
                    events = await session.push_audio(raw_bytes)
                    for ev in events:
                        await websocket.send_text(ev.model_dump_json())

            elif message.get("text"):
                raw_text = message["text"]
                try:
                    payload = json.loads(raw_text)
                    msg_type = payload.get("type")

                    if msg_type == "session_start":
                        start_msg = SessionStartMessage.model_validate(payload)
                        if is_mock:
                            session = MockCallSession(call_id=call_id)
                        else:
                            assert engine is not None
                            sess_cfg = SessionConfig(
                                mode=start_msg.mode,
                                telephony_profile=start_msg.telephony_profile,
                                language_hint=start_msg.language_hint,
                            )
                            session, ready_ev = engine.start_session(
                                call_id=call_id,
                                config=sess_cfg,
                                contacts=start_msg.contacts,
                                resume=start_msg.resume,
                            )
                            await websocket.send_text(ready_ev.model_dump_json())

                    elif msg_type == "config_update":
                        if session and hasattr(session, "update_config"):
                            await session.update_config(telephony_profile=payload.get("telephony_profile"))

                    elif msg_type == "session_end":
                        if session:
                            summary = await session.end()
                            await websocket.send_text(summary.model_dump_json())
                            break
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass
    finally:
        if session and hasattr(session, "end"):
            try:
                await session.end()
            except Exception:
                pass
