"""
SatyaSwar - Trusted-Contact Verification REST API
Member 2: Backend, Infrastructure, Database and Security

Provides REST endpoints for initiating out-of-band verification requests,
polling verification state, submitting responder confirmations/denials with
match codes, and broadcasting real-time updates over WebSocket streams.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from firebase_admin import firestore

from app.config import get_settings
from app.dependencies.auth import AuthUser, get_current_user
from app.models.enums import ActionType, ContactStatus, SessionStatus, VerificationStatus
from app.models.schemas import (
    VerificationCreateRequest,
    VerificationCreateResponse,
    VerificationRequest,
    VerificationRespondRequest,
)
from app.repositories import calls as calls_repo
from app.repositories import contacts as contacts_repo
from app.repositories import verification as verification_repo
from app.services.firebase import get_firestore_client
from app.websocket.connection import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Verification"])


def generate_match_code() -> str:
    """Generates a cryptographically random 2-digit match code (10-99)."""
    return f"{secrets.randbelow(90) + 10:02d}"


def compute_code_hash(code: str) -> str:
    """Computes HMAC-SHA256 hash of match code using application secret."""
    settings = get_settings()
    secret = (settings.verification_hmac_secret or "satyaswar_verification_secret_key").encode()
    return hmac.new(secret, code.strip().encode(), hashlib.sha256).hexdigest()


@router.post("/verifications", response_model=VerificationCreateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/verification", response_model=VerificationCreateResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_verification(
    payload: VerificationCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> VerificationCreateResponse:
    """
    Initiates an independent out-of-band verification request.

    Authorization & Validation:
    - Session must be owned by the caller.
    - Target contact must have an accepted trusted-contact relationship with caller.
    - Generates a 2-digit match code challenge (stored hashed).
    - Notifies requester's active WebSocket stream.
    """
    session_id = payload.session_id
    target_uid = payload.target_uid

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'session_id' (or 'callId') is required",
        )
    if not target_uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'target_uid' (or 'contact_id') is required",
        )

    # Validate session ownership
    try:
        session = calls_repo.get_owned_session(session_id, current_user.uid)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call session not found")

    if session.status not in (SessionStatus.CREATED, SessionStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot initiate verification for session in state: {session.status.value}",
        )

    # Validate that target_uid has an ACCEPTED contact relationship with current_user
    db = get_firestore_client()
    contacts_query = (
        db.collection("trusted_contacts")
        .where("owner_uid", "==", current_user.uid)
        .where("contact_uid", "==", target_uid)
        .where("status", "==", ContactStatus.ACCEPTED.value)
        .limit(1)
        .stream()
    )
    if not list(contacts_query):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Target user is not a confirmed trusted contact",
        )

    # Generate 2-digit challenge match code
    match_code = generate_match_code()
    code_hash = compute_code_hash(match_code)
    settings = get_settings()

    ver_req = verification_repo.create_verification_request(
        session_id=session_id,
        requester_id=current_user.uid,
        contact_user_id=target_uid,
        claimed_identity=payload.claimed_identity or "Unknown",
        action_type=payload.action_type,
        amount=payload.amount,
        ttl_seconds=settings.verification_ttl_seconds,
        code_hash=code_hash,
        max_attempts=settings.verification_max_attempts,
    )

    # Update session verification status
    db.collection("call_sessions").document(session_id).update({
        "verification_status": VerificationStatus.PENDING.value,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    # Broadcast verification update to active WebSocket connections
    await manager.broadcast(session_id, {
        "type": "verification_update",
        "session_id": session_id,
        "verification_id": ver_req.id,
        "status": VerificationStatus.PENDING.value,
        "match_code": match_code,
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

    return VerificationCreateResponse(
        verification_id=ver_req.id,
        session_id=session_id,
        target_uid=target_uid,
        match_code=match_code,
        status=VerificationStatus.PENDING,
        expires_at=ver_req.expires_at,
    )


@router.get("/verifications/{verification_id}", response_model=VerificationRequest)
@router.get("/verification/{verification_id}", response_model=VerificationRequest, include_in_schema=False)
def get_verification(
    verification_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> VerificationRequest:
    """
    Retrieves verification status.
    Only the requester OR the designated contact may inspect.
    """
    return verification_repo.get_verification_request(verification_id, current_user.uid)


@router.post("/verifications/{verification_id}/respond", response_model=VerificationRequest)
@router.post("/verification/{verification_id}/respond", response_model=VerificationRequest, include_in_schema=False)
async def respond_verification(
    verification_id: str,
    payload: VerificationRespondRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> VerificationRequest:
    """
    Responds to a verification request (approve or deny).

    Authorization & Validation:
    - ONLY the designated contact_user_id may respond (HTTP 403).
    - If match code was issued, provided code must match.
    - Terminal states cannot be altered (HTTP 409).
    - Broadcasts update over WebSocket.
    """
    approve = payload.approve
    if approve is None:
        if payload.decision:
            dec = payload.decision.strip().lower()
            if dec in ("confirm", "approve", "approved", "true"):
                approve = True
            elif dec in ("deny", "denied", "reject", "rejected", "false"):
                approve = False
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Field 'decision' must be 'confirm' or 'deny'",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must provide 'approve' (bool) or 'decision' ('confirm' | 'deny')",
            )

    code_hash = compute_code_hash(payload.selected_code) if payload.selected_code else None

    updated_req = verification_repo.respond_to_verification_request(
        request_id=verification_id,
        responder_uid=current_user.uid,
        approve=approve,
        provided_code_hash=code_hash,
    )

    # Update call session verification status
    db = get_firestore_client()
    db.collection("call_sessions").document(updated_req.session_id).update({
        "verification_status": updated_req.status.value,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    # Broadcast resolution to WebSocket
    await manager.broadcast(updated_req.session_id, {
        "type": "verification_update",
        "session_id": updated_req.session_id,
        "verification_id": updated_req.id,
        "status": updated_req.status.value,
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

    return updated_req


@router.post("/verifications/{verification_id}/cancel", response_model=VerificationRequest)
@router.post("/verification/{verification_id}/cancel", response_model=VerificationRequest, include_in_schema=False)
async def cancel_verification(
    verification_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> VerificationRequest:
    """
    Cancels an active pending verification request.
    Only the requester may cancel.
    """
    updated_req = verification_repo.cancel_verification_request(verification_id, current_user.uid)

    # Update call session verification status
    db = get_firestore_client()
    db.collection("call_sessions").document(updated_req.session_id).update({
        "verification_status": VerificationStatus.CANCELLED.value,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    # Broadcast cancel to WebSocket
    await manager.broadcast(updated_req.session_id, {
        "type": "verification_update",
        "session_id": updated_req.session_id,
        "verification_id": updated_req.id,
        "status": VerificationStatus.CANCELLED.value,
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

    return updated_req


@router.get("/verifications", response_model=list[VerificationRequest])
@router.get("/verification", response_model=list[VerificationRequest], include_in_schema=False)
def list_inbound_verifications(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AuthUser = Depends(get_current_user),
) -> list[VerificationRequest]:
    """
    Lists verification requests where current user is the designated contact.
    Enables in-app polling for responders without push notifications.
    """
    db = get_firestore_client()
    query = db.collection("verification_requests").where("contact_user_id", "==", current_user.uid)

    if status_filter:
        query = query.where("status", "==", status_filter.upper())

    results = []
    for doc in query.stream():
        d = doc.to_dict()
        results.append(
            VerificationRequest(
                id=doc.id,
                session_id=d.get("session_id", ""),
                requester_id=d.get("requester_id", ""),
                contact_user_id=d.get("contact_user_id", ""),
                claimed_identity=d.get("claimed_identity", ""),
                action_type=ActionType(d.get("action_type", ActionType.OTHER)),
                amount=d.get("amount"),
                status=VerificationStatus(d.get("status", VerificationStatus.PENDING)),
                code_hash=d.get("code_hash"),
                attempts=d.get("attempts", 0),
                max_attempts=d.get("max_attempts", 3),
                created_at=d.get("created_at"),
                expires_at=d.get("expires_at"),
                responded_at=d.get("responded_at"),
            )
        )
    return results

