"""
SatyaSwar - Users Repository
Member 2: Backend, Infrastructure, Database and Security

Manages user profile persistence, updates, and account deletion workflows in Cloud Firestore.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status
from firebase_admin import auth as fb_auth, firestore
from google.cloud import firestore as gcf

from app.models.enums import AccountStatus
from app.models.schemas import UserProfile, UserUpdate
from app.services.firebase import get_firestore_client

logger = logging.getLogger(__name__)
COLLECTION = "users"


def get_or_create_user(uid: str, email: str = "", name: str = "") -> UserProfile:
    """
    Retrieves the user profile document for the given Firebase UID.
    If the document does not exist, atomically creates it using token claims.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(uid)
    snap = doc_ref.get()

    if snap.exists:
        data = snap.to_dict() or {}
        return UserProfile(
            uid=uid,
            name=data.get("name", name),
            email=data.get("email", email),
            phone=data.get("phone"),
            account_status=data.get("account_status", AccountStatus.ACTIVE),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    # First-time profile creation
    now = firestore.SERVER_TIMESTAMP
    profile_data = {
        "uid": uid,
        "name": name,
        "email": email,
        "phone": None,
        "account_status": AccountStatus.ACTIVE.value,
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(profile_data)
    logger.info("Created new user profile in Firestore: uid=%s", uid)

    return UserProfile(
        uid=uid,
        name=name,
        email=email,
        phone=None,
        account_status=AccountStatus.ACTIVE,
        created_at=None,
        updated_at=None,
    )


def get_user_profile(uid: str) -> UserProfile:
    """
    Retrieves user profile for the given UID.
    Raises HTTP 404 if not found.
    """
    db = get_firestore_client()
    snap = db.collection(COLLECTION).document(uid).get()
    if not snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    data = snap.to_dict() or {}
    return UserProfile(
        uid=uid,
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone"),
        account_status=data.get("account_status", AccountStatus.ACTIVE),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def update_user_profile(uid: str, update_data: UserUpdate) -> UserProfile:
    """
    Updates approved profile fields (name, phone) for the user.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(uid)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    updates = {}
    if update_data.name is not None:
        updates["name"] = update_data.name.strip()
    if update_data.phone is not None:
        updates["phone"] = update_data.phone.strip()

    if updates:
        updates["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.update(updates)

    # Return refreshed profile
    updated_snap = doc_ref.get()
    data = updated_snap.to_dict() or {}
    return UserProfile(
        uid=uid,
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone"),
        account_status=data.get("account_status", AccountStatus.ACTIVE),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def mark_account_pending_deletion(uid: str) -> None:
    """
    Transitions account status to PENDING_DELETION prior to full data scrubbing.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION).document(uid)
    snap = doc_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    doc_ref.update({
        "account_status": AccountStatus.PENDING_DELETION.value,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info("Marked account pending deletion: uid=%s", uid)


def execute_complete_account_deletion(uid: str) -> None:
    """
    Executes complete GDPR-compliant account deletion:
    1. Removes contacts where owner_uid == uid or contact_uid == uid.
    2. Removes all call sessions and call history records.
    3. Removes all verification requests.
    4. Removes registered device tokens.
    5. Deletes Firestore user document.
    6. Deletes Firebase Auth user account.
    """
    db = get_firestore_client()
    logger.info("Starting complete account deletion for uid=%s", uid)

    collections_by_field = [
        ("trusted_contacts", "owner_uid"),
        ("trusted_contacts", "contact_uid"),
        ("call_sessions", "user_id"),
        ("call_history", "user_id"),
        ("verification_requests", "requester_id"),
        ("verification_requests", "contact_user_id"),
        ("device_tokens", "user_id"),
    ]

    for col_name, field_name in collections_by_field:
        docs = db.collection(col_name).where(field_name, "==", uid).stream()
        for doc in docs:
            doc.reference.delete()

    # Delete user profile document
    db.collection(COLLECTION).document(uid).delete()

    # Delete Firebase Auth user
    try:
        fb_auth.delete_user(uid)
        logger.info("Deleted Firebase Auth user: uid=%s", uid)
    except fb_auth.UserNotFoundError:
        logger.warning("Firebase Auth user already missing during deletion: uid=%s", uid)
    except Exception as e:
        logger.error("Error deleting Firebase Auth user: uid=%s, error=%s", uid, e)

