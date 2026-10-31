"""
SatyaSwar - Issue 4 Regression Test Suite
REST Call Finalization, Central Decision Engine Integration, and Idempotency Tests
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthUser
from app.main import app
from app.models.enums import (
    ActionType,
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)
from app.repositories import calls as calls_repo
from app.repositories import verification as verification_repo
from tests.mock_firestore import MockFirestoreClient

USER_A = "user_issue4_alice"
USER_B = "user_issue4_bob"
CONTACT_UID = "user_issue4_contact"


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
    uid = USER_A if "alice" in token else USER_B
    return AuthUser(uid=uid, email=f"{uid}@example.com", name=uid.capitalize())


def auth_headers(user_uid: str = USER_A):
    return {"Authorization": f"Bearer mock_token_{user_uid}"}


def test_1_end_call_low_risk(client, setup_mock_db):
    """
    Test 1: REST call end for LOW risk session produces LIKELY_GENUINE.
    """
    session = calls_repo.create_session("sess_rest_low", USER_A, action_type=ActionType.OTHER)
    calls_repo.transition_session_status(session.session_id, USER_A, SessionStatus.ACTIVE, {SessionStatus.CREATED})
    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.12,
        risk_level=RiskLevel.LOW,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == SessionStatus.COMPLETED.value

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].final_outcome == FinalOutcome.LIKELY_GENUINE


def test_2_end_call_medium_risk(client, setup_mock_db):
    """
    Test 2: REST call end for MEDIUM risk session produces INSUFFICIENT_EVIDENCE (never genuine).
    """
    session = calls_repo.create_session("sess_rest_med", USER_A, action_type=ActionType.OTHER)
    calls_repo.transition_session_status(session.session_id, USER_A, SessionStatus.ACTIVE, {SessionStatus.CREATED})
    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.52,
        risk_level=RiskLevel.MEDIUM,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].final_outcome == FinalOutcome.INSUFFICIENT_EVIDENCE


def test_3_end_call_high_risk(client, setup_mock_db):
    """
    Test 3: REST call end for HIGH risk session produces LIKELY_IMPERSONATION.
    """
    session = calls_repo.create_session("sess_rest_high", USER_A, action_type=ActionType.OTHER)
    calls_repo.transition_session_status(session.session_id, USER_A, SessionStatus.ACTIVE, {SessionStatus.CREATED})
    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.89,
        risk_level=RiskLevel.HIGH,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=4,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].final_outcome == FinalOutcome.LIKELY_IMPERSONATION


def test_4_end_call_inconclusive(client, setup_mock_db):
    """
    Test 4: Inconclusive/poor evidence session must map to INSUFFICIENT_EVIDENCE (never genuine).
    """
    session = calls_repo.create_session("sess_rest_inconc", USER_A, action_type=ActionType.OTHER)
    calls_repo.transition_session_status(session.session_id, USER_A, SessionStatus.ACTIVE, {SessionStatus.CREATED})
    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.20,
        risk_level=RiskLevel.INCONCLUSIVE,
        evidence_quality=EvidenceQualityLevel.POOR,
        window_count=2,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].final_outcome == FinalOutcome.INSUFFICIENT_EVIDENCE


def test_5_end_call_unavailable(client, setup_mock_db):
    """
    Test 5: Session with UNAVAILABLE analysis must map to UNAVAILABLE (never genuine).
    """
    session = calls_repo.create_session("sess_rest_unavail", USER_A, action_type=ActionType.OTHER)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].final_outcome == FinalOutcome.UNAVAILABLE


def test_6_end_call_approved_verification(client, setup_mock_db):
    """
    Test 6: REST end call retrieves authoritative APPROVED verification.
    """
    session = calls_repo.create_session("sess_rest_appr", USER_A, action_type=ActionType.MONEY_TRANSFER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_A,
        contact_user_id=CONTACT_UID,
        claimed_identity="Priyanka",
        action_type=ActionType.MONEY_TRANSFER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_UID, approve=True)

    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.15,
        risk_level=RiskLevel.LOW,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].verification_status == VerificationStatus.APPROVED
        assert history[0].final_outcome == FinalOutcome.LIKELY_GENUINE


def test_7_end_call_denied_verification_zero_trust(client, setup_mock_db):
    """
    Test 7: Contact DENIED verification. Zero trust requires LIKELY_IMPERSONATION even with low voice risk.
    """
    session = calls_repo.create_session("sess_rest_denied", USER_A, action_type=ActionType.MONEY_TRANSFER)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_A,
        contact_user_id=CONTACT_UID,
        claimed_identity="Priyanka",
        action_type=ActionType.MONEY_TRANSFER,
    )
    verification_repo.respond_to_verification_request(ver_req.id, CONTACT_UID, approve=False)

    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.08,
        risk_level=RiskLevel.LOW,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].verification_status == VerificationStatus.DENIED
        assert history[0].final_outcome == FinalOutcome.LIKELY_IMPERSONATION


def test_8_end_call_expired_verification(client, setup_mock_db):
    """
    Test 8: Expired verification request is recognized as EXPIRED on REST finalization.
    """
    session = calls_repo.create_session("sess_rest_exp", USER_A, action_type=ActionType.OTP_CREDENTIALS)
    ver_req = verification_repo.create_verification_request(
        session_id=session.session_id,
        requester_id=USER_A,
        contact_user_id=CONTACT_UID,
        claimed_identity="Priyanka",
        action_type=ActionType.OTP_CREDENTIALS,
        ttl_seconds=120,
    )
    # Expire in DB
    setup_mock_db.collection("verification_requests").document(ver_req.id).update({
        "expires_at": datetime.now(timezone.utc) - timedelta(seconds=10),
    })

    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.88,
        risk_level=RiskLevel.HIGH,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].verification_status == VerificationStatus.EXPIRED
        assert history[0].final_outcome == FinalOutcome.LIKELY_IMPERSONATION


def test_9_end_call_sensitive_action(client, setup_mock_db):
    """
    Test 9: Sensitive action with unverified caller is held and flagged correctly.
    """
    session = calls_repo.create_session("sess_rest_sens", USER_A, action_type=ActionType.MONEY_TRANSFER)
    calls_repo.update_session_live_risk(
        session_id=session.session_id,
        user_id=USER_A,
        risk_score=0.15,
        risk_level=RiskLevel.LOW,
        evidence_quality=EvidenceQualityLevel.GOOD,
        window_count=3,
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp.status_code == 200

        history = calls_repo.list_call_history(USER_A)
        assert len(history) == 1
        assert history[0].verification_status == VerificationStatus.NOT_REQUESTED


def test_10_repeated_end_request_idempotent(client, setup_mock_db):
    """
    Test 10: Repeated calls to POST /calls/{id}/end return HTTP 200 idempotently.
    """
    session = calls_repo.create_session("sess_rest_repeat", USER_A, action_type=ActionType.OTHER)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp1 = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp1.status_code == 200
        assert resp1.json()["status"] == SessionStatus.COMPLETED.value

        # Second call
        resp2 = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        assert resp2.status_code == 200
        assert resp2.json()["status"] == SessionStatus.COMPLETED.value


def test_11_duplicate_history_prevention(client, setup_mock_db):
    """
    Test 11: Exactly one history record is stored even if end is called multiple times.
    """
    session = calls_repo.create_session("sess_rest_dup_hist", USER_A, action_type=ActionType.OTHER)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))
        client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_A))

        history = calls_repo.list_call_history(USER_A)
        matching = [h for h in history if h.session_id == session.session_id]
        assert len(matching) == 1


def test_12_ownership_violations_rejected(client, setup_mock_db):
    """
    Test 12: User B attempting to end User A's session is rejected with HTTP 404
    (preventing existence leakage and access violation).
    """
    session = calls_repo.create_session("sess_alice_owned", USER_A, action_type=ActionType.OTHER)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        resp = client.post(f"/api/v1/calls/{session.session_id}/end", headers=auth_headers(USER_B))
        assert resp.status_code == 404

