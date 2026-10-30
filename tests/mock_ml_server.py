"""
SatyaSwar - Mock ML Audio Analysis Server
Member 2: Backend, Infrastructure, Database and Security

Provides an in-process or standalone mock of Member 3's ML inference service
for testing audio streaming, scoring loops, timeouts, and error scenarios.
"""

from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

app = FastAPI(title="SatyaSwar Mock ML Server", version="1.0.0")


class MockMLConfig:
    """Configurable switches to simulate delays, errors, and custom scores."""

    fixed_spoof_score: Optional[float] = None
    fixed_evidence_quality: Optional[float] = None
    simulate_delay_seconds: float = 0.0
    simulate_failure: bool = False
    simulate_http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    request_count: int = 0


config = MockMLConfig()


def reset_mock_ml_config() -> None:
    """Reset configuration back to default normal operation."""
    config.fixed_spoof_score = None
    config.fixed_evidence_quality = None
    config.simulate_delay_seconds = 0.0
    config.simulate_failure = False
    config.simulate_http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    config.request_count = 0


class MLPredictionResponse(BaseModel):
    session_id: str
    window_id: int
    spoof_score: float
    evidence_quality: float
    speech_duration: float
    processing_time_ms: int


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(
    request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    x_window_id: Optional[str] = Header(None, alias="X-Window-Id"),
    x_sample_rate: Optional[str] = Header("16000", alias="X-Sample-Rate"),
):
    import asyncio

    config.request_count += 1

    if config.simulate_delay_seconds > 0:
        await asyncio.sleep(config.simulate_delay_seconds)

    if config.simulate_failure:
        raise HTTPException(
            status_code=config.simulate_http_status,
            detail="Simulated ML inference failure",
        )

    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing audio payload",
        )

    session_id = x_session_id or "unknown_session"
    try:
        window_id = int(x_window_id or "0")
    except ValueError:
        window_id = 0

    spoof_score = (
        config.fixed_spoof_score if config.fixed_spoof_score is not None else 0.85
    )
    evidence_quality = (
        config.fixed_evidence_quality
        if config.fixed_evidence_quality is not None
        else 0.90
    )

    return MLPredictionResponse(
        session_id=session_id,
        window_id=window_id,
        spoof_score=spoof_score,
        evidence_quality=evidence_quality,
        speech_duration=3.5,
        processing_time_ms=120,
    )

