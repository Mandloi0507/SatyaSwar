"""
SatyaSwar - Call Sessions REST Routes
Member 2: Backend, Infrastructure, Database and Security

Implements call session initialization, history inspection, live session monitoring,
and session termination under /api/v1/calls.
CRITICAL: Declares static routes (e.g. /history) BEFORE dynamic routes (e.g. /{session_id}).
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.config import get_settings
from app.dependencies.auth import AuthUser, get_current_user
from app.models.enums import (
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.models.schemas import (
    CallCreateRequest,
    CallCreateResponse,
    CallHistoryItem,
    CallSession,
)
from app.repositories import calls as calls_repo

router = APIRouter(prefix="/api/v1/calls", tags=["Calls"])


@router.post("", response_model=CallCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/start", response_model=CallCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_call_session(
    request: Optional[CallCreateRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
) -> CallCreateResponse:
    """
    Initializes a new call analysis session.
    Generates a unique session ID and returns the corresponding WebSocket connection details.
    """
    session_id = f"call_{secrets.token_hex(6)}"
    session = calls_repo.create_session(session_id=session_id, user_id=current_user.uid)
    settings = get_settings()

    return CallCreateResponse(
        session_id=session.session_id,
        status=session.status,
        ws_url=f"/ws/call/{session.session_id}",
        config={
            "window_seconds": settings.audio_window_seconds,
            "hop_seconds": settings.audio_hop_seconds,
            "sample_rate": settings.audio_sample_rate,
            "channels": settings.audio_channels,
            "sample_width_bytes": settings.audio_sample_width_bytes,
        },
        server_time=datetime.now(timezone.utc),
    )


# ------------------------------------------------------------------------------
# Route-Order Rule: Static path /history declared BEFORE dynamic path /{session_id}
# ------------------------------------------------------------------------------
@router.get("/history", response_model=list[CallHistoryItem])
async def get_user_call_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max history items to return"),
    current_user: AuthUser = Depends(get_current_user),
) -> list[CallHistoryItem]:
    """
    Retrieves the authenticated user's paginated call history.
    Strictly isolated to records owned by the caller.
    """
    return calls_repo.list_call_history(user_id=current_user.uid, limit=limit)


@router.get("/{session_id}", response_model=CallSession)
async def get_session_details(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> CallSession:
    """
    Retrieves status and live metrics for a specific call session.
    Enforces strict ownership: returns HTTP 404 if the session belongs to another user.
    """
    return calls_repo.get_owned_session(session_id=session_id, user_id=current_user.uid)


@router.post("/{session_id}/end", response_model=CallSession)
async def end_call_session(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> CallSession:
    """
    Terminates an active or pending call session and transitions status to COMPLETED.
    """
    session = calls_repo.get_owned_session(session_id=session_id, user_id=current_user.uid)

    if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED):
        return session

    # Transition to COMPLETED
    updated = calls_repo.transition_session_status(
        session_id=session_id,
        user_id=current_user.uid,
        new_status=SessionStatus.COMPLETED,
        allowed_from={SessionStatus.CREATED, SessionStatus.ACTIVE, SessionStatus.PROCESSING},
    )

    # Automatically write call history record if not already recorded
    calls_repo.complete_session_and_persist_history(
        session_id=session_id,
        user_id=current_user.uid,
        claimed_contact=session.session_id,
        risk_score=session.latest_risk_score,
        risk_level=session.risk_level,
        evidence_quality=session.evidence_quality,
        verification_status=session.verification_status,
        final_outcome=FinalOutcome.LIKELY_GENUINE if session.risk_level == RiskLevel.LOW else FinalOutcome.SUSPICIOUS,
    )

    return updated


@router.get("/{session_id}/result")
async def get_session_result(
    session_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """
    Returns the final structured analysis result for a completed session.
    """
    session = calls_repo.get_owned_session(session_id=session_id, user_id=current_user.uid)

    return {
        "session_id": session.session_id,
        "status": session.status,
        "risk_level": session.risk_level,
        "latest_risk_score": session.latest_risk_score,
        "evidence_quality": session.evidence_quality,
        "verification_status": session.verification_status,
        "windows_processed": session.window_count,
        "start_time": session.start_time,
        "end_time": session.end_time,
    }

