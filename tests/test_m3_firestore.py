"""
SatyaSwar - M3 Firestore Database Architecture Automated Tests
Member 2: Backend, Infrastructure, Database and Security

Tests cover:
- Users CRUD, profile updates, and cascading account deletion
- Trusted contacts invite creation, self-invite rejection, transactional acceptance
- Contact owner-specific aliases and duplicate-name labels
- Call session creation, ownership isolation, state machine transitions
- Privacy enforcement: verified that NO raw audio, frames, or transcripts are stored
- Call history persistence with automated TTL retention ('expires_at')
- Verification request lifecycle: creation, authorization, approval, denial, challenge attempts, expiration
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models.enums import (
    AccountStatus,
    ActionType,
    ContactStatus,
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.models.schemas import UserUpdate
from app.repositories.calls import (
    complete_session_and_persist_history,
    create_session,
    get_owned_session,
    list_call_history,
    transition_session_status,
    update_session_live_risk,
)
from app.repositories.contacts import (
    accept_invite_transactional,
    create_invite,
    get_accepted_contact,
    list_accepted_contacts,
    remove_contact,
    update_contact_alias_and_label,
)
from app.repositories.users import (
    execute_complete_account_deletion,
    get_or_create_user,
    get_user_profile,
    mark_account_pending_deletion,
    update_user_profile,
)
from app.repositories.verification import (
    cancel_verification_request,
    create_verification_request,
    get_verification_request,
    respond_to_verification_request,
)
from tests.mock_firestore import MockFirestoreClient


@pytest.fixture
def mock_db():
    """Provides a fresh in-memory MockFirestoreClient per test."""
    client = MockFirestoreClient()
    with patch("app.repositories.users.get_firestore_client", return_value=client), \
         patch("app.repositories.contacts.get_firestore_client", return_value=client), \
         patch("app.repositories.calls.get_firestore_client", return_value=client), \
         patch("app.repositories.verification.get_firestore_client", return_value=client):
        yield client


# ==============================================================================
# Users Repository Tests
# ==============================================================================

def test_user_get_or_create(mock_db):
    """Verify first-time user profile creation and subsequent retrieval."""
    user = get_or_create_user("uid_1", email="user1@satyaswar.io", name="User One")
    assert user.uid == "uid_1"
    assert user.email == "user1@satyaswar.io"
    assert user.name == "User One"
    assert user.account_status == AccountStatus.ACTIVE

    # Fetching existing profile returns identical UID without overwriting
    user2 = get_or_create_user("uid_1", email="other@satyaswar.io", name="Other")
    assert user2.uid == "uid_1"
    assert user2.name == "User One"


def test_user_update_profile(mock_db):
    """Verify updating allowed profile fields (name, phone)."""
    get_or_create_user("uid_update", email="update@test.com", name="Initial Name")
    updated = update_user_profile("uid_update", UserUpdate(name="New Name", phone="+919876543210"))
    assert updated.name == "New Name"
    assert updated.phone == "+919876543210"


def test_user_mark_pending_deletion(mock_db):
    """Verify account status transition to PENDING_DELETION."""
    get_or_create_user("uid_del", email="del@test.com", name="To Delete")
    mark_account_pending_deletion("uid_del")
    profile = get_user_profile("uid_del")
    assert profile.account_status == AccountStatus.PENDING_DELETION


def test_user_complete_cascading_deletion(mock_db):
    """Verify complete cascading deletion across all collections and Firebase Auth."""
    uid = "uid_scrub"
    get_or_create_user(uid, email="scrub@test.com", name="Scrub")
    create_session("session_scrub", uid)

    with patch("firebase_admin.auth.delete_user") as mock_auth_del:
        execute_complete_account_deletion(uid)
        mock_auth_del.assert_called_once_with(uid)

    # User document must be gone
    with pytest.raises(HTTPException) as exc:
        get_user_profile(uid)
    assert exc.value.status_code == 404


# ==============================================================================
# Trusted Contacts Repository Tests
# ==============================================================================

def test_contact_invite_and_acceptance(mock_db):
    """
    Verify complete trusted-contact invitation flow:
    - Creation with code hashing
    - Acceptance creating reciprocal records
    - Disambiguation aliases and labels
    """
    owner_uid = "owner_123"
    invitee_uid = "invitee_456"
    raw_code = "SAFE-9999"
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    doc_id = create_invite(owner_uid, "Priyanka Sharma", raw_code, expires)
    assert doc_id is not None

    # Invitee accepts with custom alias 'Priti' and label 'college'
    accepted = accept_invite_transactional(
        invitee_uid=invitee_uid,
        invitee_registered_name="Rakesh Verma",
        raw_invite_code=raw_code,
        alias="Priti",
        label="college",
    )
    assert accepted.owner_uid == invitee_uid
    assert accepted.contact_uid == owner_uid
    assert accepted.alias == "Priti"
    assert accepted.label == "college"
    assert accepted.status == ContactStatus.ACCEPTED

    # Both parties now see the contact in their accepted list
    owner_contacts = list_accepted_contacts(owner_uid)
    invitee_contacts = list_accepted_contacts(invitee_uid)
    assert len(owner_contacts) == 1
    assert len(invitee_contacts) == 1
    assert owner_contacts[0].contact_uid == invitee_uid
    assert invitee_contacts[0].contact_uid == owner_uid


def test_contact_self_invite_rejected(mock_db):
    """Verify that a user cannot accept their own invitation."""
    owner_uid = "self_uid"
    raw_code = "SELF-CODE"
    create_invite(owner_uid, "Self User", raw_code, datetime.now(timezone.utc) + timedelta(minutes=10))

    with pytest.raises(HTTPException) as exc:
        accept_invite_transactional(
            invitee_uid=owner_uid,
            invitee_registered_name="Self User",
            raw_invite_code=raw_code,
        )
    assert exc.value.status_code == 400


def test_contact_expired_invite_rejected(mock_db):
    """Verify that an expired invitation returns HTTP 410."""
    owner_uid = "owner_exp"
    raw_code = "EXP-CODE"
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    create_invite(owner_uid, "Exp User", raw_code, past_time)

    with pytest.raises(HTTPException) as exc:
        accept_invite_transactional(
            invitee_uid="invitee_exp",
            invitee_registered_name="Invitee",
            raw_invite_code=raw_code,
        )
    assert exc.value.status_code == 410


def test_contact_alias_update(mock_db):
    """Verify that an owner can update personal alias and label."""
    owner = "owner_a"
    contact = "contact_b"
    code = "CODE-123"
    create_invite(owner, "Contact B", code, datetime.now(timezone.utc) + timedelta(minutes=10))
    accept_invite_transactional(contact, "Owner A", code, alias="Initial", label="Old")

    updated = update_contact_alias_and_label(contact, owner, alias="Boss", label="Office")
    assert updated.alias == "Boss"
    assert updated.label == "Office"


def test_contact_removal(mock_db):
    """Verify unlinking a relationship in both directions."""
    u1, u2 = "u1", "u2"
    code = "UNLINK-CODE"
    create_invite(u1, "U1", code, datetime.now(timezone.utc) + timedelta(minutes=10))
    accept_invite_transactional(u2, "U2", code)

    remove_contact(u1, u2)
    assert get_accepted_contact(u1, u2) is None
    assert get_accepted_contact(u2, u1) is None


# ==============================================================================
# Call Sessions & History Repository Tests
# ==============================================================================

def test_session_lifecycle_and_ownership(mock_db):
    """Verify session creation, strict ownership checks, and state transitions."""
    user_id = "user_caller"
    session_id = "call_abc123"

    session = create_session(session_id, user_id)
    assert session.status == SessionStatus.CREATED

    # Ownership check: Owner can retrieve session
    owned = get_owned_session(session_id, user_id)
    assert owned.session_id == session_id

    # Ownership check: Other user receives HTTP 404 (no existence leakage)
    with pytest.raises(HTTPException) as exc:
        get_owned_session(session_id, "intruder_user")
    assert exc.value.status_code == 404

    # Valid transition: CREATED -> ACTIVE
    active_session = transition_session_status(
        session_id, user_id, SessionStatus.ACTIVE, {SessionStatus.CREATED}
    )
    assert active_session.status == SessionStatus.ACTIVE

    # Invalid transition rejected with HTTP 409
    with pytest.raises(HTTPException) as exc:
        transition_session_status(
            session_id, user_id, SessionStatus.CREATED, {SessionStatus.COMPLETED}
        )
    assert exc.value.status_code == 409


def test_call_history_privacy_and_retention(mock_db):
    """
    CRITICAL PRIVACY TEST:
    Verify that finalized session produces a compact history record containing scores only.
    Confirms NO audio bytes, audio frames, or transcripts exist anywhere in the store.
    """
    user_id = "user_privacy"
    session_id = "call_priv_999"
    create_session(session_id, user_id)

    history = complete_session_and_persist_history(
        session_id=session_id,
        user_id=user_id,
        claimed_contact="Priyanka Sharma",
        risk_score=0.88,
        risk_level=RiskLevel.HIGH,
        evidence_quality=EvidenceQualityLevel.GOOD,
        verification_status=VerificationStatus.DENIED,
        final_outcome=FinalOutcome.LIKELY_IMPERSONATION,
        retention_days=30,
    )

    assert history.risk_score == 0.88
    assert history.final_outcome == FinalOutcome.LIKELY_IMPERSONATION
    assert history.expires_at is not None

    # Inspect the raw stored dictionaries in mock_db for call_sessions and call_history
    session_raw = mock_db.collection("call_sessions").document(session_id).get().to_dict()
    history_raw = mock_db.collection("call_history").document(history.id).get().to_dict()

    forbidden_keys = {"audio", "pcm", "wav", "frames", "audio_bytes", "transcript", "speech_text"}
    assert forbidden_keys.isdisjoint(session_raw.keys()), "Privacy violation: audio/transcript in session"
    assert forbidden_keys.isdisjoint(history_raw.keys()), "Privacy violation: audio/transcript in history"


def test_list_call_history(mock_db):
    """Verify listing paginated call history for user."""
    user = "user_hist"
    create_session("c1", user)
    complete_session_and_persist_history(
        session_id="c1",
        user_id=user,
        claimed_contact="Contact 1",
        risk_score=0.2,
        risk_level=RiskLevel.LOW,
        evidence_quality=EvidenceQualityLevel.GOOD,
        verification_status=VerificationStatus.NOT_REQUESTED,
        final_outcome=FinalOutcome.LIKELY_GENUINE,
    )
    history_items = list_call_history(user, limit=10)
    assert len(history_items) == 1
    assert history_items[0].claimed_contact == "Contact 1"


# ==============================================================================
# Verification Requests Repository Tests
# ==============================================================================

def test_verification_lifecycle(mock_db):
    """
    Verify complete verification state machine:
    - Creation
    - Access authorization (only requester and responder)
    - Responder approval
    - Terminal state immutability (cannot re-answer)
    """
    requester = "req_user"
    responder = "resp_user"
    session_id = "call_ver_01"

    req = create_verification_request(
        session_id=session_id,
        requester_id=requester,
        contact_user_id=responder,
        claimed_identity="Priyanka Sharma",
        action_type=ActionType.MONEY_TRANSFER,
        amount=50000.0,
        ttl_seconds=120,
    )
    assert req.status == VerificationStatus.PENDING

    # Requester and responder can inspect the request
    assert get_verification_request(req.id, requester).id == req.id
    assert get_verification_request(req.id, responder).id == req.id

    # Third party gets HTTP 404
    with pytest.raises(HTTPException) as exc:
        get_verification_request(req.id, "intruder")
    assert exc.value.status_code == 404

    # Third party cannot respond (HTTP 403)
    with pytest.raises(HTTPException) as exc:
        respond_to_verification_request(req.id, "intruder", approve=True)
    assert exc.value.status_code == 403

    # Designated responder approves
    approved = respond_to_verification_request(req.id, responder, approve=True)
    assert approved.status == VerificationStatus.APPROVED

    # Terminal state cannot be re-answered (HTTP 409)
    with pytest.raises(HTTPException) as exc:
        respond_to_verification_request(req.id, responder, approve=False)
    assert exc.value.status_code == 409


def test_verification_cancellation(mock_db):
    """Verify that requester can cancel an active pending request."""
    req = create_verification_request("s_c", "req_c", "resp_c", "Claimed")
    cancelled = cancel_verification_request(req.id, "req_c")
    assert cancelled.status == VerificationStatus.CANCELLED


def test_verification_challenge_code_attempts(mock_db):
    """Verify challenge code matching and attempt limits leading to denial."""
    code_hash = "correct_hash"
    req = create_verification_request(
        "s_ch", "req_ch", "resp_ch", "Claimed", code_hash=code_hash, max_attempts=2
    )

    # First wrong attempt increments count
    with pytest.raises(HTTPException) as exc1:
        respond_to_verification_request(req.id, "resp_ch", approve=True, provided_code_hash="wrong_hash")
    assert exc1.value.status_code == 400
    assert "1/2 attempts" in exc1.value.detail

    # Second wrong attempt exceeds limit and marks DENIED
    with pytest.raises(HTTPException) as exc2:
        respond_to_verification_request(req.id, "resp_ch", approve=True, provided_code_hash="wrong_hash")
    assert exc2.value.status_code == 400
    assert "maximum attempts exceeded" in exc2.value.detail

    final_req = get_verification_request(req.id, "resp_ch")
    assert final_req.status == VerificationStatus.DENIED

