"""
SatyaSwar - Module 7 Automated Test Suite
Trusted-Contact Verification Workflow Tests
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import ContactStatus, SessionStatus, VerificationStatus
from app.repositories import calls as calls_repo
from app.repositories import contacts as contacts_repo
from tests.mock_firestore import MockFirestoreClient

USER_A_UID = "user_m7_alice"
USER_B_UID = "user_m7_bob"
USER_C_UID = "user_m7_charlie"


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_db = MockFirestoreClient()
    with patch("app.repositories.verification.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.calls.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.contacts.get_firestore_client", return_value=mock_db), \
         patch("app.routes.verification.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


def make_user_token(uid: str) -> str:
    return f"mock_token_{uid}"


def mock_verify_token(token: str):
    from app.dependencies.auth import AuthUser
    if not token or not token.startswith("mock_token_"):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = token.replace("mock_token_", "")
    return AuthUser(uid=uid, email=f"{uid}@example.com", name=uid.capitalize())


def setup_test_environment():
    """Helper to establish an active session for Alice and a linked relationship with Bob."""
    from datetime import datetime, timedelta, timezone
    import secrets

    # Create active session for Alice
    session = calls_repo.create_session("sess_m7_01", USER_A_UID)
    calls_repo.transition_session_status(
        session_id=session.session_id,
        user_id=USER_A_UID,
        new_status=SessionStatus.ACTIVE,
        allowed_from={SessionStatus.CREATED},
    )

    # Establish accepted contact link between Alice and Bob
    raw_code = f"INVITE-{secrets.token_hex(4).upper()}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    contacts_repo.create_invite(
        owner_uid=USER_A_UID,
        owner_registered_name="Alice",
        raw_invite_code=raw_code,
        expires_at=expires_at,
    )
    contacts_repo.accept_invite_transactional(
        invitee_uid=USER_B_UID,
        invitee_registered_name="Bob Builder",
        raw_invite_code=raw_code,
        alias="Bob",
        label="friend",
    )
    return session


def test_create_verification_request_success(client):
    """Alice creates an out-of-band verification request targeting Bob."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        payload = {
            "session_id": session.session_id,
            "target_uid": USER_B_UID,
            "claimed_identity": "Bob",
            "action_type": "money_transfer",
            "amount": 25000.0,
        }
        resp = client.post(
            "/api/v1/verifications",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == session.session_id
        assert data["target_uid"] == USER_B_UID
        assert data["status"] == "PENDING"
        assert len(data["match_code"]) == 2  # 2-digit match code challenge
        assert "verification_id" in data


def test_create_verification_fails_if_contact_not_linked(client):
    """Alice trying to verify against unlinked Charlie must return HTTP 403 Forbidden."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        payload = {
            "session_id": session.session_id,
            "target_uid": USER_C_UID,  # Not linked!
            "claimed_identity": "Charlie",
        }
        resp = client.post(
            "/api/v1/verifications",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_create_verification_fails_if_duplicate_pending(client):
    """Initiating a second pending verification for the same session and contact returns HTTP 409."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        payload = {
            "session_id": session.session_id,
            "target_uid": USER_B_UID,
            "claimed_identity": "Bob",
        }
        resp1 = client.post(
            "/api/v1/verifications",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp1.status_code == 201

        # Second request must fail with 409 Conflict
        resp2 = client.post(
            "/api/v1/verifications",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp2.status_code == 409
        assert resp2.json()["error"]["code"] == "CONFLICT"


def test_get_verification_authorization(client):
    """Only Alice (requester) and Bob (designated contact) can view the request; Charlie gets 404."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        token_b = make_user_token(USER_B_UID)
        token_c = make_user_token(USER_C_UID)

        create_resp = client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ver_id = create_resp.json()["verification_id"]

        # Alice checks
        resp_a = client.get(f"/api/v1/verifications/{ver_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 200

        # Bob checks
        resp_b = client.get(f"/api/v1/verifications/{ver_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200

        # Charlie checks (anti-enumeration 404)
        resp_c = client.get(f"/api/v1/verifications/{ver_id}", headers={"Authorization": f"Bearer {token_c}"})
        assert resp_c.status_code == 404


def test_respond_verification_approve_with_code(client):
    """Bob responds with confirm and matching 2-digit code -> request becomes APPROVED."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        token_b = make_user_token(USER_B_UID)

        create_resp = client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ver_data = create_resp.json()
        ver_id = ver_data["verification_id"]
        match_code = ver_data["match_code"]

        # Bob responds with correct match code
        resp = client.post(
            f"/api/v1/verifications/{ver_id}/respond",
            json={"decision": "confirm", "selected_code": match_code},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"


def test_respond_verification_wrong_responder_forbidden(client):
    """Alice (or any third party) cannot respond to a request designated for Bob."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)

        create_resp = client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ver_id = create_resp.json()["verification_id"]

        # Alice attempts to answer her own request
        resp = client.post(
            f"/api/v1/verifications/{ver_id}/respond",
            json={"decision": "confirm"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_respond_verification_code_mismatch(client):
    """Bob entering a wrong match code receives HTTP 400 Bad Request."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        token_b = make_user_token(USER_B_UID)

        create_resp = client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ver_id = create_resp.json()["verification_id"]

        # Bob enters wrong code
        resp = client.post(
            f"/api/v1/verifications/{ver_id}/respond",
            json={"decision": "confirm", "selected_code": "999"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 400
        assert "mismatch" in resp.json()["error"]["message"]


def test_cancel_verification_by_requester(client):
    """Alice cancels the pending verification request."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        token_b = make_user_token(USER_B_UID)

        create_resp = client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ver_id = create_resp.json()["verification_id"]

        # Bob tries to cancel (forbidden)
        resp_b = client.post(f"/api/v1/verifications/{ver_id}/cancel", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 403

        # Alice cancels
        resp_a = client.post(f"/api/v1/verifications/{ver_id}/cancel", headers={"Authorization": f"Bearer {token_a}"})
        assert resp_a.status_code == 200
        assert resp_a.json()["status"] == "CANCELLED"


def test_inbound_verifications_list_polling(client):
    """Bob polls for pending verification requests where he is the designated contact."""
    session = setup_test_environment()

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        token_b = make_user_token(USER_B_UID)

        # Alice creates verification targeting Bob
        client.post(
            "/api/v1/verifications",
            json={"session_id": session.session_id, "target_uid": USER_B_UID},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # Bob polls inbound requests
        resp = client.get("/api/v1/verifications?status=PENDING", headers={"Authorization": f"Bearer {token_b}"})
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        assert items[0]["contact_user_id"] == USER_B_UID
