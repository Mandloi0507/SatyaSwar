"""
SatyaSwar - Issue 3 Regression Test Suite
Final Risk Decision & Authoritative Verification State Integration Tests
"""

import asyncio
from datetime import datetime, timedelta, timezone
import struct
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthUser
from app.main import app
from app.models.enums import (
    ActionType,
    FinalOutcome,
    RiskLevel,
    VerificationStatus,
)
from app.repositories import calls as calls_repo
from app.repositories import verification as verification_repo
from app.services.ml_service import MLClient, MLUnavailable
from app.websocket.audio_frame import EXPECTED_PCM_BYTES
from tests.mock_firestore import MockFirestoreClient

USER_ID = "user_issue3_caller"
CONTACT_ID = "user_issue3_contact"


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_db = MockFirestoreClient()
    with patch("app.services.firebase.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.calls.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.verification.get_firestore_client", return_value=mock_db), \
         patch("app.routes.verification.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


def mock_verify_token(token: str):
    return AuthUser(uid=USER_ID, email=f"{USER_ID}@example.com", name="Caller")


def make_auth_headers():
    return {"Authorization": "Bearer mock_valid_token"}


def create_frame_m1(seq: int = 0, is_last: bool = True) -> bytes:
    header = struct.pack(
        "<BBHIIQ",
        1,  # version
        1 if is_last else 0,
        0,
        seq,
        0,
        int(time.time() * 1000),
    )
    return header + (b"\x00" * EXPECTED_PCM_BYTES)


def test_1_outcome_not_requested_low_risk(client, setup_mock_db):
    """
    Test 1: Verification NOT_REQUESTED with low spoof risk and casual action.
    Must produce LIKELY_GENUINE, NOT_REQUESTED, and shouldHoldAction=False.
    """
    session = calls_repo.create_session("sess_not_requested", USER_ID, action_type=ActionType.OTHER)

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.12, "evidence_quality": 0.90}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()  # ready
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()  # score
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.LIKELY_GENUINE.value
            assert outcome["verificationStatus"] == VerificationStatus.NOT_REQUESTED.value
            assert outcome["shouldHoldAction"] is False


def test_2_outcome_pending_verification_sensitive_action(client, setup_mock_db):
    """
    Test 2: Verification is PENDING when call ends for a sensitive action (MONEY_TRANSFER).
    Even with low voice spoof risk, sensitive action must be held (shouldHoldAction=True).
    """
    session = calls_repo.create_session("sess_pending", USER_ID, action_type=ActionType.MONEY_TRANSFER)
    verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.MONEY_TRANSFER,
        ttl_seconds=120,
    )

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.15, "evidence_quality": 0.90}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()  # ready
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()  # score
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.LIKELY_GENUINE.value
            assert outcome["verificationStatus"] == VerificationStatus.PENDING.value
            assert outcome["shouldHoldAction"] is True
            assert outcome["actionType"] == ActionType.MONEY_TRANSFER.value


def test_3_outcome_approved_verification(client, setup_mock_db):
    """
    Test 3: Verification was APPROVED by trusted contact.
    Low voice risk + APPROVED -> LIKELY_GENUINE, shouldHoldAction=False.
    """
    session = calls_repo.create_session("sess_approved", USER_ID, action_type=ActionType.MONEY_TRANSFER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.MONEY_TRANSFER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_ID, approve=True)

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.10, "evidence_quality": 0.92}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.LIKELY_GENUINE.value
            assert outcome["verificationStatus"] == VerificationStatus.APPROVED.value
            assert outcome["shouldHoldAction"] is False
            assert "Verified through the linked account" in outcome["headline"]


def test_4_outcome_denied_verification_zero_trust(client, setup_mock_db):
    """
    Test 4: Verification DENIED by contact.
    Zero Trust Requirement: A denied verification MUST NOT be treated as successful,
    even if the voice spoof score is very low!
    """
    session = calls_repo.create_session("sess_denied", USER_ID, action_type=ActionType.OTHER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.OTHER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_ID, approve=False)

    async def mock_low_spoof(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.05, "evidence_quality": 0.95}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_low_spoof):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.LIKELY_IMPERSONATION.value
            assert outcome["verificationStatus"] == VerificationStatus.DENIED.value
            assert outcome["shouldHoldAction"] is True
            assert "Likely impersonation" in outcome["headline"]


def test_5_outcome_expired_verification(client, setup_mock_db):
    """
    Test 5: Verification request expired prior to call finalization.
    Server evaluates authoritative state as EXPIRED and holds sensitive action.
    """
    session = calls_repo.create_session("sess_expired", USER_ID, action_type=ActionType.OTP_CREDENTIALS)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.OTP_CREDENTIALS,
        ttl_seconds=120,
    )

    # Force expiration in mock database
    past_dt = datetime.now(timezone.utc) - timedelta(seconds=10)
    setup_mock_db.collection("verification_requests").document(ver_req.id).update({
        "expires_at": past_dt,
    })

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.15, "evidence_quality": 0.90}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["verificationStatus"] == VerificationStatus.EXPIRED.value
            assert outcome["shouldHoldAction"] is True


def test_6_outcome_cancelled_verification(client, setup_mock_db):
    """
    Test 6: Verification request was CANCELLED by requester.
    Preserves CANCELLED state and holds sensitive action.
    """
    session = calls_repo.create_session("sess_cancelled", USER_ID, action_type=ActionType.CONFIDENTIAL_INFO)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.CONFIDENTIAL_INFO,
    )
    verification_repo.cancel_verification_request(ver_req.id, USER_ID)

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.18, "evidence_quality": 0.88}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["verificationStatus"] == VerificationStatus.CANCELLED.value
            assert outcome["shouldHoldAction"] is True


def test_7_outcome_no_contact_match(client, setup_mock_db):
    """
    Test 7: Caller does not match any registered trusted contact.
    Session status is NO_CONTACT_MATCH without a verification request record.
    Must output INSUFFICIENT_EVIDENCE and distinct headline.
    """
    session = calls_repo.create_session("sess_no_match", USER_ID, action_type=ActionType.MONEY_TRANSFER)
    setup_mock_db.collection("call_sessions").document(session.session_id).update({
        "verification_status": VerificationStatus.NO_CONTACT_MATCH.value,
    })

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.20, "evidence_quality": 0.85}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.INSUFFICIENT_EVIDENCE.value
            assert outcome["verificationStatus"] == VerificationStatus.NO_CONTACT_MATCH.value
            assert "Cannot verify through SatyaSwar" in outcome["headline"]
            assert outcome["shouldHoldAction"] is True


def test_8_high_risk_plus_approved_verification_conflicting_signals(client, setup_mock_db):
    """
    Test 8: High Voice Risk + APPROVED verification -> CONFLICTING_SIGNALS.
    Zero Trust Guarantee: High spoof risk must NOT be downgraded to safe simply
    because the trusted contact confirmed.
    """
    session = calls_repo.create_session("sess_conflict", USER_ID, action_type=ActionType.MONEY_TRANSFER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.MONEY_TRANSFER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_ID, approve=True)

    async def mock_high_spoof(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.92, "evidence_quality": 0.95}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_high_spoof):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.CONFLICTING_SIGNALS.value
            assert outcome["verificationStatus"] == VerificationStatus.APPROVED.value
            assert outcome["shouldHoldAction"] is True
            assert "Conflicting signals" in outcome["headline"]


def test_9_high_risk_plus_denied_verification(client, setup_mock_db):
    """
    Test 9: High Voice Risk + DENIED verification -> LIKELY_IMPERSONATION.
    Both signals agree on malicious impersonation.
    """
    session = calls_repo.create_session("sess_high_denied", USER_ID, action_type=ActionType.MONEY_TRANSFER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_ID,
        contact_user_id=CONTACT_ID,
        claimed_identity="Alice",
        action_type=ActionType.MONEY_TRANSFER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_ID, approve=False)

    async def mock_high_spoof(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.95, "evidence_quality": 0.95}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_high_spoof):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.LIKELY_IMPERSONATION.value
            assert outcome["verificationStatus"] == VerificationStatus.DENIED.value
            assert outcome["shouldHoldAction"] is True


def test_10_sensitive_action_insufficient_evidence(client, setup_mock_db):
    """
    Test 10: Uncertain/inconclusive audio evidence for sensitive action (MONEY_TRANSFER).
    Must result in INSUFFICIENT_EVIDENCE and shouldHoldAction=True.
    """
    session = calls_repo.create_session("sess_inconclusive", USER_ID, action_type=ActionType.MONEY_TRANSFER)

    # Score in uncertain band (0.50)
    async def mock_uncertain_score(self, session_id, window_id, pcm_bytes):
        return {"session_id": session_id, "window_id": window_id, "spoof_score": 0.50, "evidence_quality": 0.85}

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_uncertain_score):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            _ = ws.receive_json()
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.INSUFFICIENT_EVIDENCE.value
            assert outcome["shouldHoldAction"] is True
            assert "Insufficient evidence" in outcome["headline"]


def test_11_ml_unavailable_preserves_unavailable_outcome(client, setup_mock_db):
    """
    Test 11: When ML upstream fails consecutively or worker is unavailable,
    final outcome is UNAVAILABLE (never defaulting to safe or LOW).
    """
    session = calls_repo.create_session("sess_ml_unavail", USER_ID, action_type=ActionType.OTHER)

    async def mock_failing_ml(self, session_id, window_id, pcm_bytes):
        raise MLUnavailable("Upstream ML service offline")

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_failing_ml):

        with client.websocket_connect(f"/ws/v1/calls/{session.session_id}", headers=make_auth_headers()) as ws:
            _ = ws.receive_json()  # ready
            # Send 3 frames to trigger consecutive ML failure threshold
            ws.send_bytes(create_frame_m1(seq=0, is_last=False))
            ws.send_bytes(create_frame_m1(seq=1, is_last=False))
            ws.send_bytes(create_frame_m1(seq=2, is_last=True))

            messages = []
            while True:
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg.get("type") == "outcome":
                        break
                except Exception:
                    break

            outcome = next(m for m in messages if m.get("type") == "outcome")
            assert outcome["finalOutcome"] == FinalOutcome.UNAVAILABLE.value
            assert "unavailable" in outcome["headline"].lower()

