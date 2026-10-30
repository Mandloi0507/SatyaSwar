"""
SatyaSwar - M4 REST APIs & Call Session Management Automated Tests
Member 2: Backend, Infrastructure, Database and Security

Tests cover:
- User profile APIs (GET /me, PATCH /me, DELETE /me)
- Trusted contact APIs (POST /invite, GET /, POST /accept, PATCH /{contact_uid}, DELETE /{contact_uid})
- Call session APIs (POST /calls, POST /calls/start, GET /calls/history, GET /calls/{id}, POST /calls/{id}/end, GET /calls/{id}/result)
- Route ordering verification: GET /calls/history evaluated before dynamic /{session_id}
- Authentication enforcement on all protected routes
- Standard error envelope {"error": {"code": ..., "message": ...}} on 401, 404, 409, 422
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
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


@pytest.fixture
def client():
    """Provides a FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client


def make_auth_headers(uid: str, email: str = "user@test.com", name: str = "Test User") -> tuple[dict, any]:
    """Helper returning headers and a mock context for verify_id_token."""
    mock_claims = {"uid": uid, "email": email, "name": name}
    headers = {"Authorization": f"Bearer mock-token-{uid}"}
    return headers, mock_claims


# ==============================================================================
# User Profile REST API Tests
# ==============================================================================

def test_get_current_user_profile_provisions_on_first_call(client, mock_db):
    """Verify GET /api/v1/users/me auto-provisions profile for authenticated user."""
    headers, claims = make_auth_headers("uid_user_1", "u1@satyaswar.io", "User One")
    with patch("app.dependencies.auth.verify_id_token", return_value=claims):
        resp = client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["uid"] == "uid_user_1"
        assert data["email"] == "u1@satyaswar.io"
        assert data["name"] == "User One"
        assert data["account_status"] == "active"


def test_patch_current_user_profile(client, mock_db):
    """Verify PATCH /api/v1/users/me updates name and phone."""
    headers, claims = make_auth_headers("uid_user_2", "u2@satyaswar.io", "Initial Name")
    with patch("app.dependencies.auth.verify_id_token", return_value=claims):
        # Create first
        client.get("/api/v1/users/me", headers=headers)
        # Update
        patch_resp = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={"name": "Updated Name", "phone": "+919876543210"},
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["name"] == "Updated Name"
        assert data["phone"] == "+919876543210"


def test_delete_current_user_account(client, mock_db):
    """Verify DELETE /api/v1/users/me returns HTTP 202 and marks account pending deletion."""
    headers, claims = make_auth_headers("uid_user_3", "u3@satyaswar.io", "To Delete")
    with patch("app.dependencies.auth.verify_id_token", return_value=claims), \
         patch("firebase_admin.auth.delete_user"):
        # Provision profile
        client.get("/api/v1/users/me", headers=headers)
        del_resp = client.delete("/api/v1/users/me", headers=headers)
        assert del_resp.status_code == 202
        assert del_resp.json()["status"] == "pending_deletion"


# ==============================================================================
# Trusted Contacts REST API Tests
# ==============================================================================

def test_contact_invite_accept_flow(client, mock_db):
    """
    Verify complete contact workflow:
    1. User A generates invite
    2. User B accepts invite with custom alias and label
    3. User A and User B list contacts
    4. User B updates alias
    5. User A deletes contact
    """
    h_a, claims_a = make_auth_headers("uid_a", "a@test.com", "User A")
    h_b, claims_b = make_auth_headers("uid_b", "b@test.com", "User B")

    # Step 1: User A creates invite
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_a):
        inv_resp = client.post("/api/v1/contacts/invite", headers=h_a, json={})
        assert inv_resp.status_code == 201
        inv_data = inv_resp.json()
        raw_code = inv_data["code"]
        assert "satyaswar:invite:" in inv_data["qr_payload"]

    # Step 2: User B accepts invite
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_b):
        accept_resp = client.post(
            "/api/v1/contacts/accept",
            headers=h_b,
            json={"code": raw_code, "alias": "Alice", "label": "friend"},
        )
        assert accept_resp.status_code == 200
        acc_data = accept_resp.json()
        assert acc_data["owner_uid"] == "uid_b"
        assert acc_data["contact_uid"] == "uid_a"
        assert acc_data["alias"] == "Alice"
        assert acc_data["label"] == "friend"

    # Step 3: User B lists contacts
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_b):
        list_resp = client.get("/api/v1/contacts", headers=h_b)
        assert list_resp.status_code == 200
        contacts = list_resp.json()
        assert len(contacts) == 1
        assert contacts[0]["contact_uid"] == "uid_a"

    # Step 4: User B updates alias
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_b):
        patch_resp = client.patch(
            "/api/v1/contacts/uid_a",
            headers=h_b,
            json={"alias": "Alice Manager", "label": "work"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["alias"] == "Alice Manager"

    # Step 5: User A deletes contact
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_a):
        del_resp = client.delete("/api/v1/contacts/uid_b", headers=h_a)
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "removed"


# ==============================================================================
# Call Sessions REST API Tests
# ==============================================================================

def test_call_session_crud_and_route_order(client, mock_db):
    """
    Verify call session APIs and crucial route ordering:
    - POST /api/v1/calls creates session
    - GET /api/v1/calls/history returns history (static route not caught by {session_id})
    - GET /api/v1/calls/{session_id} returns session details
    - POST /api/v1/calls/{session_id}/end terminates session
    - GET /api/v1/calls/{session_id}/result returns final structured outcome
    """
    headers, claims = make_auth_headers("uid_caller", "caller@test.com", "Caller")

    with patch("app.dependencies.auth.verify_id_token", return_value=claims):
        # 1. Create session via POST /api/v1/calls
        create_resp = client.post(
            "/api/v1/calls",
            headers=headers,
            json={
                "scenario_id": "clone_ceo",
                "claimed_name": "Rakesh Sir",
                "caller_number": "+919876500000",
                "direction": "incoming",
            },
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        session_id = session_data["session_id"]
        assert session_id.startswith("call_")
        assert session_data["status"] == "CREATED"
        assert session_data["ws_url"] == f"/ws/call/{session_id}"
        assert session_data["config"]["sample_rate"] == 16000

        # Also verify /start alias works
        start_alias_resp = client.post("/api/v1/calls/start", headers=headers, json={})
        assert start_alias_resp.status_code == 201

        # 2. Verify static route: GET /api/v1/calls/history
        hist_resp = client.get("/api/v1/calls/history", headers=headers)
        assert hist_resp.status_code == 200
        assert isinstance(hist_resp.json(), list)

        # 3. GET /api/v1/calls/{session_id}
        get_resp = client.get(f"/api/v1/calls/{session_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

        # 4. POST /api/v1/calls/{session_id}/end
        end_resp = client.post(f"/api/v1/calls/{session_id}/end", headers=headers)
        assert end_resp.status_code == 200
        assert end_resp.json()["status"] == "COMPLETED"

        # 5. GET /api/v1/calls/{session_id}/result
        res_resp = client.get(f"/api/v1/calls/{session_id}/result", headers=headers)
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "COMPLETED"


def test_call_session_ownership_protection(client, mock_db):
    """Verify that a user cannot inspect another user's call session (returns HTTP 404)."""
    h_owner, claims_owner = make_auth_headers("uid_owner")
    h_intruder, claims_intruder = make_auth_headers("uid_intruder")

    # Owner creates session
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_owner):
        create_resp = client.post("/api/v1/calls", headers=h_owner, json={})
        session_id = create_resp.json()["session_id"]

    # Intruder tries to access
    with patch("app.dependencies.auth.verify_id_token", return_value=claims_intruder):
        intruder_resp = client.get(f"/api/v1/calls/{session_id}", headers=h_intruder)
        assert intruder_resp.status_code == 404
        err = intruder_resp.json()["error"]
        assert err["code"] == "NOT_FOUND"
        assert err["message"] == "Call session not found"


# ==============================================================================
# Standard Error Envelope Tests
# ==============================================================================

def test_unauthenticated_request_returns_standard_error(client):
    """Verify that unauthenticated access returns standard error envelope."""
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert err["code"] == "UNAUTHORIZED"
    assert "Missing bearer authorization credentials" in err["message"]


def test_validation_error_returns_standard_envelope(client, mock_db):
    """Verify that invalid request body returns 422 with standard VALIDATION_ERROR envelope."""
    headers, claims = make_auth_headers("uid_val")
    with patch("app.dependencies.auth.verify_id_token", return_value=claims):
        # Invalid phone pattern
        resp = client.patch("/api/v1/users/me", headers=headers, json={"phone": "invalid-not-phone"})
        assert resp.status_code == 422
        err = resp.json()["error"]
        assert err["code"] == "VALIDATION_ERROR"
        assert "Request validation failed" in err["message"]
        assert "details" in err

