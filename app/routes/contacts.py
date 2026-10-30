"""
SatyaSwar - Trusted Contacts REST Routes
Member 2: Backend, Infrastructure, Database and Security

Implements contact invitation generation, listing, acceptance with alias/label,
updates, and unlinking under /api/v1/contacts.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import AuthUser, get_current_user
from app.models.schemas import (
    ContactUpdateRequest,
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteCreateResponse,
    TrustedContact,
)
from app.repositories import contacts as contacts_repo

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])


def generate_secure_invite_code() -> str:
    """Generates an 8-character hyphenated alphanumeric code (e.g. K7M2-9QX4)."""
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous characters like 0, O, 1, I
    clean_alphabet = "".join(c for c in alphabet if c not in "0O1I")
    part1 = "".join(secrets.choice(clean_alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(clean_alphabet) for _ in range(4))
    return f"{part1}-{part2}"


@router.post("/invite", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_invitation(
    request: InviteCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> InviteCreateResponse:
    """
    Generates a single-use random invitation code and QR payload.
    The raw code is returned to the client and stored in Firestore only as a SHA-256 hash.
    Default validity: 15 minutes.
    """
    raw_code = generate_secure_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    owner_name = current_user.name or "Trusted Contact"

    contacts_repo.create_invite(
        owner_uid=current_user.uid,
        owner_registered_name=owner_name,
        raw_invite_code=raw_code,
        expires_at=expires_at,
    )

    return InviteCreateResponse(
        code=raw_code,
        expires_at=expires_at,
        qr_payload=f"satyaswar:invite:{raw_code}",
    )


@router.get("", response_model=list[TrustedContact])
async def list_trusted_contacts(
    current_user: AuthUser = Depends(get_current_user),
) -> list[TrustedContact]:
    """
    Lists all accepted trusted contacts for the authenticated user.
    Returns owner-specific aliases and disambiguation labels.
    """
    return contacts_repo.list_accepted_contacts(owner_uid=current_user.uid)


@router.post("/accept", response_model=TrustedContact)
async def accept_contact_invitation(
    request: InviteAcceptRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> TrustedContact:
    """
    Accepts an invitation code and establishes reciprocal contact entries.
    Allows specifying an owner-private alias and disambiguation label.
    """
    invitee_name = current_user.name or "Trusted Contact"
    return contacts_repo.accept_invite_transactional(
        invitee_uid=current_user.uid,
        invitee_registered_name=invitee_name,
        raw_invite_code=request.code,
        alias=request.alias,
        label=request.label,
    )


@router.patch("/{contact_uid}", response_model=TrustedContact)
async def update_contact_details(
    contact_uid: str,
    request: ContactUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> TrustedContact:
    """
    Updates the caller's personal alias and disambiguation label for a linked contact.
    """
    return contacts_repo.update_contact_alias_and_label(
        owner_uid=current_user.uid,
        contact_uid=contact_uid,
        alias=request.alias,
        label=request.label,
    )


@router.delete("/{contact_uid}", status_code=status.HTTP_200_OK)
async def remove_trusted_contact(
    contact_uid: str,
    current_user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    """
    Unlinks the contact relationship between both users.
    """
    contacts_repo.remove_contact(
        owner_uid=current_user.uid,
        contact_uid=contact_uid,
    )
    return {"status": "removed", "contact_uid": contact_uid}

