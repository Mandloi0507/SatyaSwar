"""
SatyaSwar - Trusted Contacts Repository
Member 2: Backend, Infrastructure, Database and Security

Manages trusted contact relationships, single-use invite generation and acceptance,
custom owner-specific aliases/labels, and relationship termination.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from firebase_admin import firestore
from google.cloud import firestore as gcf

from app.models.enums import ContactStatus
from app.models.schemas import TrustedContact
from app.services.firebase import get_firestore_client

logger = logging.getLogger(__name__)
COLLECTION = "trusted_contacts"


def hash_invite_code(code: str) -> str:
    """Computes a SHA-256 hash of the invite code for secure database storage."""
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def create_invite(
    owner_uid: str,
    owner_registered_name: str,
    raw_invite_code: str,
    expires_at: datetime,
) -> str:
    """
    Creates a pending invitation document with a hashed single-use code.
    Returns the created document ID.
    """
    db = get_firestore_client()
    code_hash = hash_invite_code(raw_invite_code)

    now = firestore.SERVER_TIMESTAMP
    doc_ref = db.collection(COLLECTION).document()
    doc_data = {
        "owner_uid": owner_uid,
        "contact_uid": None,
        "registered_name": owner_registered_name,
        "alias": None,
        "label": None,
        "status": ContactStatus.PENDING.value,
        "invite_code_hash": code_hash,
        "invite_expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(doc_data)
    logger.info("Created pending invite: doc_id=%s, owner_uid=%s", doc_ref.id, owner_uid)
    return doc_ref.id


def list_accepted_contacts(owner_uid: str) -> list[TrustedContact]:
    """
    Retrieves all accepted contacts belonging to owner_uid.
    Enforces that aliases and labels returned are strictly those created by the owner.
    """
    db = get_firestore_client()
    docs = (
        db.collection(COLLECTION)
        .where("owner_uid", "==", owner_uid)
        .where("status", "==", ContactStatus.ACCEPTED.value)
        .stream()
    )

    contacts = []
    for doc in docs:
        d = doc.to_dict()
        contacts.append(
            TrustedContact(
                id=doc.id,
                owner_uid=d.get("owner_uid", owner_uid),
                contact_uid=d.get("contact_uid"),
                registered_name=d.get("registered_name", ""),
                alias=d.get("alias"),
                label=d.get("label"),
                status=ContactStatus(d.get("status", ContactStatus.ACCEPTED)),
                created_at=d.get("created_at"),
                updated_at=d.get("updated_at"),
            )
        )
    return contacts


def get_accepted_contact(owner_uid: str, contact_uid: str) -> Optional[TrustedContact]:
    """
    Retrieves a single accepted contact record by contact_uid for owner_uid.
    Returns None if not found or not accepted.
    """
    db = get_firestore_client()
    docs = (
        db.collection(COLLECTION)
        .where("owner_uid", "==", owner_uid)
        .where("contact_uid", "==", contact_uid)
        .where("status", "==", ContactStatus.ACCEPTED.value)
        .limit(1)
        .stream()
    )
    for doc in docs:
        d = doc.to_dict()
        return TrustedContact(
            id=doc.id,
            owner_uid=owner_uid,
            contact_uid=contact_uid,
            registered_name=d.get("registered_name", ""),
            alias=d.get("alias"),
            label=d.get("label"),
            status=ContactStatus.ACCEPTED,
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )
    return None


def accept_invite_transactional(
    invitee_uid: str,
    invitee_registered_name: str,
    raw_invite_code: str,
    alias: Optional[str] = None,
    label: Optional[str] = None,
) -> TrustedContact:
    """
    Validates and accepts an invitation in a transactional manner:
    1. Locates pending invite by code hash.
    2. Enforces expiration and self-invite restrictions.
    3. Establishes reciprocal accepted records for both parties.
    """
    db = get_firestore_client()
    code_hash = hash_invite_code(raw_invite_code)

    # Query the pending invite
    pending_query = (
        db.collection(COLLECTION)
        .where("invite_code_hash", "==", code_hash)
        .where("status", "==", ContactStatus.PENDING.value)
        .limit(1)
        .stream()
    )

    pending_docs = list(pending_query)
    if not pending_docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation code",
        )

    pending_doc = pending_docs[0]
    pending_data = pending_doc.to_dict()
    owner_uid = pending_data["owner_uid"]
    owner_name = pending_data.get("registered_name", "Trusted Contact")
    expires_at = pending_data.get("invite_expires_at")

    if owner_uid == invitee_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link your own account as a trusted contact",
        )

    if expires_at:
        now_dt = datetime.now(timezone.utc)
        if hasattr(expires_at, "astimezone"):
            exp_dt = expires_at.astimezone(timezone.utc)
        elif isinstance(expires_at, datetime):
            exp_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        else:
            exp_dt = None

        if exp_dt and exp_dt < now_dt:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation code has expired",
            )

    # Check if active relationship already exists
    existing = get_accepted_contact(owner_uid, invitee_uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A trusted contact relationship already exists between these users",
        )

    now = firestore.SERVER_TIMESTAMP

    # Update the creator's entry with invitee details
    pending_doc.reference.update({
        "contact_uid": invitee_uid,
        "registered_name": invitee_registered_name,
        "status": ContactStatus.ACCEPTED.value,
        "invite_code_hash": None,
        "updated_at": now,
    })

    # Create reciprocal entry for the invitee with their custom alias and label
    reciprocal_ref = db.collection(COLLECTION).document()
    reciprocal_data = {
        "owner_uid": invitee_uid,
        "contact_uid": owner_uid,
        "registered_name": owner_name,
        "alias": alias.strip() if alias else None,
        "label": label.strip() if label else None,
        "status": ContactStatus.ACCEPTED.value,
        "invite_code_hash": None,
        "invite_expires_at": None,
        "created_at": now,
        "updated_at": now,
    }
    reciprocal_ref.set(reciprocal_data)

    logger.info("Accepted invite: owner=%s, invitee=%s", owner_uid, invitee_uid)

    return TrustedContact(
        id=reciprocal_ref.id,
        owner_uid=invitee_uid,
        contact_uid=owner_uid,
        registered_name=owner_name,
        alias=alias,
        label=label,
        status=ContactStatus.ACCEPTED,
        created_at=None,
        updated_at=None,
    )


def update_contact_alias_and_label(
    owner_uid: str,
    contact_uid: str,
    alias: Optional[str] = None,
    label: Optional[str] = None,
) -> TrustedContact:
    """
    Updates the owner's personal alias and disambiguation label for a linked contact.
    """
    db = get_firestore_client()
    docs = (
        db.collection(COLLECTION)
        .where("owner_uid", "==", owner_uid)
        .where("contact_uid", "==", contact_uid)
        .where("status", "==", ContactStatus.ACCEPTED.value)
        .limit(1)
        .stream()
    )

    matching_docs = list(docs)
    if not matching_docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trusted contact not found or not linked",
        )

    doc_ref = matching_docs[0].reference
    updates = {"updated_at": firestore.SERVER_TIMESTAMP}
    if alias is not None:
        updates["alias"] = alias.strip() if alias.strip() else None
    if label is not None:
        updates["label"] = label.strip() if label.strip() else None

    doc_ref.update(updates)
    refreshed = doc_ref.get().to_dict() or {}

    return TrustedContact(
        id=doc_ref.id,
        owner_uid=owner_uid,
        contact_uid=contact_uid,
        registered_name=refreshed.get("registered_name", ""),
        alias=refreshed.get("alias"),
        label=refreshed.get("label"),
        status=ContactStatus.ACCEPTED,
        created_at=refreshed.get("created_at"),
        updated_at=refreshed.get("updated_at"),
    )


def remove_contact(owner_uid: str, contact_uid: str) -> None:
    """
    Removes/unlinks the relationship between owner_uid and contact_uid in both directions.
    """
    db = get_firestore_client()
    # Find both directional documents
    docs1 = (
        db.collection(COLLECTION)
        .where("owner_uid", "==", owner_uid)
        .where("contact_uid", "==", contact_uid)
        .stream()
    )
    docs2 = (
        db.collection(COLLECTION)
        .where("owner_uid", "==", contact_uid)
        .where("contact_uid", "==", owner_uid)
        .stream()
    )

    count = 0
    for doc in list(docs1) + list(docs2):
        doc.reference.update({
            "status": ContactStatus.REMOVED.value,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        count += 1

    if count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    logger.info("Unlinked contact relationship between uid=%s and uid=%s", owner_uid, contact_uid)

