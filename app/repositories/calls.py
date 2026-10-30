"""
SatyaSwar - Call Sessions & History Repository
Member 2: Backend, Infrastructure, Database and Security

Manages call session lifecycles, live score streaming updates, state transitions,
and compact privacy-preserving history records with automated retention TTL.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Set

from fastapi import HTTPException, status
from firebase_admin import firestore

from app.models.enums import (
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.models.schemas import CallHistoryItem, CallSession
from app.services.firebase import get_firestore_client

logger = logging.getLogger(__name__)

COL_SESSIONS = "call_sessions"
COL_HISTORY = "call_history"


def create_session(session_id: str, user_id: str) -> CallSession:
    """
    Creates a new call session record in CREATED state.
    """
    db = get_firestore_client()
    now = firestore.SERVER_TIMESTAMP
    doc_ref = db.collection(COL_SESSIONS).document(session_id)

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "status": SessionStatus.CREATED.value,
        "start_time": None,
        "end_time": None,
        "latest_risk_score": None,
        "risk_level": RiskLevel.UNAVAILABLE.value,
        "evidence_quality": EvidenceQualityLevel.POOR.value,
        "verification_status": VerificationStatus.NOT_REQUESTED.value,
        "window_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(session_data)
    logger.info("Created call session: session_id=%s, user_id=%s", session_id, user_id)

    return CallSession(
        session_id=session_id,
        user_id=user_id,
        status=SessionStatus.CREATED,
        created_at=None,
        updated_at=None,
    )


def get_owned_session(session_id: str, user_id: str) -> CallSession:
    """
    Retrieves a session and verifies ownership.
    Returns HTTP 404 if the session does not exist or belongs to another user
    (preventing ID enumeration and existence leakage).
    """
    db = get_firestore_client()
    doc_ref = db.collection(COL_SESSIONS).document(session_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call session not found",
        )

    data = snap.to_dict() or {}
    if data.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call session not found",
        )

    return CallSession(
        session_id=session_id,
        user_id=user_id,
        status=SessionStatus(data.get("status", SessionStatus.CREATED)),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        latest_risk_score=data.get("latest_risk_score"),
        risk_level=RiskLevel(data.get("risk_level", RiskLevel.UNAVAILABLE)),
        evidence_quality=EvidenceQualityLevel(data.get("evidence_quality", EvidenceQualityLevel.POOR)),
        verification_status=VerificationStatus(data.get("verification_status", VerificationStatus.NOT_REQUESTED)),
        window_count=data.get("window_count", 0),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def transition_session_status(
    session_id: str,
    user_id: str,
    new_status: SessionStatus,
    allowed_from: Set[SessionStatus],
) -> CallSession:
    """
    Safely transitions session status enforcing state-machine immutability.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COL_SESSIONS).document(session_id)
    snap = doc_ref.get()

    if not snap.exists or snap.to_dict().get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call session not found")

    current_status = SessionStatus(snap.to_dict().get("status"))
    if current_status not in allowed_from:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid session status transition from {current_status.value} to {new_status.value}",
        )

    now = firestore.SERVER_TIMESTAMP
    updates = {
        "status": new_status.value,
        "updated_at": now,
    }
    if new_status == SessionStatus.ACTIVE and current_status == SessionStatus.CREATED:
        updates["start_time"] = now

    doc_ref.update(updates)
    logger.info("Transitioned session %s from %s to %s", session_id, current_status.value, new_status.value)

    return get_owned_session(session_id, user_id)


def update_session_live_risk(
    session_id: str,
    user_id: str,
    risk_score: float,
    risk_level: RiskLevel,
    evidence_quality: EvidenceQualityLevel,
    window_count: int,
) -> None:
    """
    Updates live session metrics as audio windows are processed.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COL_SESSIONS).document(session_id)
    doc_ref.update({
        "latest_risk_score": risk_score,
        "risk_level": risk_level.value,
        "evidence_quality": evidence_quality.value,
        "window_count": window_count,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def complete_session_and_persist_history(
    session_id: str,
    user_id: str,
    claimed_contact: str,
    risk_score: Optional[float],
    risk_level: RiskLevel,
    evidence_quality: EvidenceQualityLevel,
    verification_status: VerificationStatus,
    final_outcome: FinalOutcome,
    retention_days: int = 30,
) -> CallHistoryItem:
    """
    Finalizes the live session and writes a compact, privacy-safe history item.
    Privacy Guarantee: Never stores audio bytes, frames, or speech transcripts.
    Sets 'expires_at' for Firestore TTL retention policy.
    """
    db = get_firestore_client()
    now = firestore.SERVER_TIMESTAMP

    # Transition session to COMPLETED
    session_ref = db.collection(COL_SESSIONS).document(session_id)
    session_ref.update({
        "status": SessionStatus.COMPLETED.value,
        "end_time": now,
        "latest_risk_score": risk_score,
        "risk_level": risk_level.value,
        "evidence_quality": evidence_quality.value,
        "verification_status": verification_status.value,
        "updated_at": now,
    })

    # Persist compact history summary
    expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)
    history_ref = db.collection(COL_HISTORY).document()

    history_data = {
        "user_id": user_id,
        "session_id": session_id,
        "claimed_contact": claimed_contact,
        "risk_score": risk_score,
        "risk_level": risk_level.value,
        "evidence_quality": evidence_quality.value,
        "verification_status": verification_status.value,
        "final_outcome": final_outcome.value,
        "created_at": now,
        "expires_at": expires_at,
    }
    history_ref.set(history_data)
    logger.info("Persisted call history item: doc_id=%s, session_id=%s", history_ref.id, session_id)

    return CallHistoryItem(
        id=history_ref.id,
        user_id=user_id,
        session_id=session_id,
        claimed_contact=claimed_contact,
        risk_score=risk_score,
        risk_level=risk_level,
        evidence_quality=evidence_quality,
        verification_status=verification_status,
        final_outcome=final_outcome,
        created_at=None,
        expires_at=expires_at,
    )


def list_call_history(
    user_id: str,
    limit: int = 20,
) -> list[CallHistoryItem]:
    """
    Retrieves paginated call history summaries belonging strictly to user_id.
    """
    db = get_firestore_client()
    query = (
        db.collection(COL_HISTORY)
        .where("user_id", "==", user_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )

    items = []
    for doc in query.stream():
        d = doc.to_dict()
        items.append(
            CallHistoryItem(
                id=doc.id,
                user_id=user_id,
                session_id=d.get("session_id", ""),
                claimed_contact=d.get("claimed_contact", ""),
                risk_score=d.get("risk_score"),
                risk_level=RiskLevel(d.get("risk_level", RiskLevel.UNAVAILABLE)),
                evidence_quality=EvidenceQualityLevel(d.get("evidence_quality", EvidenceQualityLevel.POOR)),
                verification_status=VerificationStatus(d.get("verification_status", VerificationStatus.NOT_REQUESTED)),
                final_outcome=FinalOutcome(d.get("final_outcome", FinalOutcome.UNAVAILABLE)),
                created_at=d.get("created_at"),
                expires_at=d.get("expires_at"),
            )
        )
    return items
