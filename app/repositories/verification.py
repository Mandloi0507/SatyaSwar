"""
SatyaSwar - Verification Requests Repository
Member 2: Backend, Infrastructure, Database and Security

Manages independent trusted-contact verification state machine, responder authorization,
challenge code validation, attempt limits, expiration enforcement, and cancellation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from firebase_admin import firestore

from app.models.enums import ActionType, VerificationStatus
from app.models.schemas import VerificationRequest
from app.services.firebase import get_firestore_client

logger = logging.getLogger(__name__)
COLLECTION = "verification_requests"


def create_verification_request(
    session_id: str,
    requester_id: str,
    contact_user_id: str,
    claimed_identity: str,
    action_type: ActionType = ActionType.OTHER,
    amount: Optional[float] = None,
    ttl_seconds: int = 120,
    code_hash: Optional[str] = None,
    max_attempts: int = 3,
) -> VerificationRequest:
    """
    Creates an independent verification request in PENDING state.
    Enforces that only one pending request exists per session/contact.
    """
    db = get_firestore_client()

    # Check for active pending request
    existing_query = (
        db.collection(COLLECTION)
        .where("session_id", "==", session_id)
        .where("contact_user_id", "==", contact_user_id)
        .where("status", "==", VerificationStatus.PENDING.value)
        .limit(1)
        .stream()
    )
    if list(existing_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active verification request is already pending for this contact",
        )

    now_dt = datetime.now(timezone.utc)
    expires_dt = now_dt + timedelta(seconds=ttl_seconds)
    server_now = firestore.SERVER_TIMESTAMP

    doc_ref = db.collection(COLLECTION).document()
    doc_data = {
        "session_id": session_id,
        "requester_id": requester_id,
        "contact_user_id": contact_user_id,
        "claimed_identity": claimed_identity,
        "action_type": action_type.value,
        "amount": amount,
        "status": VerificationStatus.PENDING.value,
        "code_hash": code_hash,
        "attempts": 0,
        "max_attempts": max_attempts,
        "created_at": server_now,
        "expires_at": expires_dt,
        "responded_at": None,
    }
    doc_ref.set(doc_data)
    logger.info("Created verification request: doc_id=%s, requester=%s, contact=%s", doc_ref.id, requester_id, contact_user_id)

    return VerificationRequest(
        id=doc_ref.id,
        session_id=session_id,
        requester_id=requester_id,
        contact_user_id=contact_user_id,
        claimed_identity=claimed_identity,
        action_type=action_type,
        amount=amount,
        status=VerificationStatus.PENDING,
        code_hash=code_hash,
        attempts=0,
        max_attempts=max_attempts,
        created_at=None,
        expires_at=expires_dt,
        responded_at=None,
    )


def get_verification_request(request_id: str, caller_uid: str) -> VerificationRequest:
    """
    Retrieves verification request and enforces authorization.
    Only the requester OR the designated contact may inspect the request.
    Automatically checks and marks expired requests as EXPIRED.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification request not found",
        )

    d = snap.to_dict() or {}
    requester_id = d.get("requester_id")
    contact_user_id = d.get("contact_user_id")

    # Access control: caller must be requester or designated contact
    if caller_uid != requester_id and caller_uid != contact_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification request not found",
        )

    current_status = VerificationStatus(d.get("status", VerificationStatus.PENDING))
    expires_at = d.get("expires_at")

    # Check for expiration if still pending
    if current_status == VerificationStatus.PENDING and expires_at:
        now_dt = datetime.now(timezone.utc)
        if hasattr(expires_at, "astimezone"):
            exp_dt = expires_at.astimezone(timezone.utc)
        elif isinstance(expires_at, datetime):
            exp_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        else:
            exp_dt = None

        if exp_dt and exp_dt < now_dt:
            doc_ref.update({
                "status": VerificationStatus.EXPIRED.value,
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            current_status = VerificationStatus.EXPIRED

    return VerificationRequest(
        id=doc_ref.id,
        session_id=d.get("session_id", ""),
        requester_id=requester_id,
        contact_user_id=contact_user_id,
        claimed_identity=d.get("claimed_identity", ""),
        action_type=ActionType(d.get("action_type", ActionType.OTHER)),
        amount=d.get("amount"),
        status=current_status,
        code_hash=d.get("code_hash"),
        attempts=d.get("attempts", 0),
        max_attempts=d.get("max_attempts", 3),
        created_at=d.get("created_at"),
        expires_at=expires_at,
        responded_at=d.get("responded_at"),
    )


def respond_to_verification_request(
    request_id: str,
    responder_uid: str,
    approve: bool,
    provided_code_hash: Optional[str] = None,
) -> VerificationRequest:
    """
    Submits responder decision (APPROVED or DENIED).
    Strict authorization: ONLY the designated contact_user_id may respond.
    Immutability: Terminal states (APPROVED, DENIED, EXPIRED, CANCELLED) cannot be re-answered.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    d = snap.to_dict() or {}
    contact_user_id = d.get("contact_user_id")

    if responder_uid != contact_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the designated trusted contact can respond to this verification request",
        )

    current_status = VerificationStatus(d.get("status", VerificationStatus.PENDING))
    if current_status != VerificationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot respond to verification request in terminal state: {current_status.value}",
        )

    # Expiry check
    expires_at = d.get("expires_at")
    if expires_at:
        now_dt = datetime.now(timezone.utc)
        if hasattr(expires_at, "astimezone"):
            exp_dt = expires_at.astimezone(timezone.utc)
        elif isinstance(expires_at, datetime):
            exp_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        else:
            exp_dt = None

        if exp_dt and exp_dt < now_dt:
            doc_ref.update({"status": VerificationStatus.EXPIRED.value})
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Verification request has expired",
            )

    # Optional challenge code verification
    expected_code_hash = d.get("code_hash")
    if expected_code_hash:
        attempts = d.get("attempts", 0) + 1
        if provided_code_hash != expected_code_hash:
            if attempts >= d.get("max_attempts", 3):
                doc_ref.update({
                    "attempts": attempts,
                    "status": VerificationStatus.DENIED.value,
                    "responded_at": firestore.SERVER_TIMESTAMP,
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Challenge code mismatch: maximum attempts exceeded; request denied",
                )
            doc_ref.update({"attempts": attempts})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Challenge code mismatch ({attempts}/{d.get('max_attempts', 3)} attempts used)",
            )

    new_status = VerificationStatus.APPROVED if approve else VerificationStatus.DENIED
    now = firestore.SERVER_TIMESTAMP
    doc_ref.update({
        "status": new_status.value,
        "responded_at": now,
        "updated_at": now,
    })
    logger.info("Verification request %s resolved as %s by responder %s", request_id, new_status.value, responder_uid)

    return get_verification_request(request_id, responder_uid)


def cancel_verification_request(request_id: str, requester_uid: str) -> VerificationRequest:
    """
    Cancels an active pending verification request.
    Only the requester may cancel.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")

    d = snap.to_dict() or {}
    if d.get("requester_id") != requester_uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this verification request",
        )

    current_status = VerificationStatus(d.get("status"))
    if current_status != VerificationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel verification request in state: {current_status.value}",
        )

    now = firestore.SERVER_TIMESTAMP
    doc_ref.update({
        "status": VerificationStatus.CANCELLED.value,
        "updated_at": now,
    })
    logger.info("Verification request %s cancelled by requester %s", request_id, requester_uid)

    return get_verification_request(request_id, requester_uid)
