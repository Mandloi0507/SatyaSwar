"""
SatyaSwar - M2 Firebase and Authentication Automated Tests
Member 2: Backend, Infrastructure, Database and Security

Tests cover:
- Valid token verification (REST & WebSocket)
- Missing, invalid, expired, revoked tokens (HTTP 401)
- Disabled user rejection (HTTP 401)
- WebSocket header-based authentication
- WebSocket first-message authentication
- WebSocket authentication timeout and invalid message handling
- Firebase Admin SDK initialization singleton safety
"""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth as fb_auth

from app.dependencies.auth import (
    WS_AUTH_FAILED_CODE,
    AuthUser,
    authenticate_ws_token,
    get_current_user,
    verify_token,
)
from app.main import app
from app.services.firebase import init_firebase


@pytest.fixture
def client():
    """Provides a TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# REST Authentication Tests
# ==============================================================================

def test_rest_auth_valid_token(client):
    """Verify that a valid Firebase ID token grants access and returns user claims."""
    mock_claims = {
        "uid": "user_test_123",
        "email": "tester@satyaswar.internal",
        "name": "Satya Tester",
    }
    with patch("app.dependencies.auth.verify_id_token", return_value=mock_claims):
        response = client.get(
            "/api/v1/auth/me-check",
            headers={"Authorization": "Bearer valid-mock-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "user_test_123"
        assert data["email"] == "tester@satyaswar.internal"
        assert data["name"] == "Satya Tester"


def test_rest_auth_missing_token(client):
    """Verify that a request lacking the Authorization header returns HTTP 401."""
    response = client.get("/api/v1/auth/me-check")
    assert response.status_code == 401
    err = response.json()["error"]
    assert err["code"] == "UNAUTHORIZED"
    assert "Missing bearer authorization credentials" in err["message"]


def test_rest_auth_invalid_token(client):
    """Verify that a malformed or invalid token returns HTTP 401."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.InvalidIdTokenError("Token is malformed"),
    ):
        response = client.get(
            "/api/v1/auth/me-check",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
        err = response.json()["error"]
        assert err["code"] == "UNAUTHORIZED"
        assert err["message"] == "Invalid or expired authentication token"


def test_rest_auth_expired_token(client):
    """Verify that an expired Firebase ID token returns HTTP 401."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.ExpiredIdTokenError("Token has expired", None),
    ):
        response = client.get(
            "/api/v1/auth/me-check",
            headers={"Authorization": "Bearer expired-token"},
        )
        assert response.status_code == 401
        err = response.json()["error"]
        assert err["code"] == "UNAUTHORIZED"
        assert err["message"] == "Invalid or expired authentication token"


def test_rest_auth_revoked_token(client):
    """Verify that a revoked token returns HTTP 401."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.RevokedIdTokenError("Token was revoked"),
    ):
        response = client.get(
            "/api/v1/auth/me-check",
            headers={"Authorization": "Bearer revoked-token"},
        )
        assert response.status_code == 401
        err = response.json()["error"]
        assert err["code"] == "UNAUTHORIZED"
        assert err["message"] == "Invalid or expired authentication token"


def test_rest_auth_disabled_user(client):
    """Verify that a disabled user account is rejected with HTTP 401."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.UserDisabledError("User account is disabled"),
    ):
        response = client.get(
            "/api/v1/auth/me-check",
            headers={"Authorization": "Bearer disabled-user-token"},
        )
        assert response.status_code == 401
        err = response.json()["error"]
        assert err["code"] == "UNAUTHORIZED"
        assert err["message"] == "Invalid or expired authentication token"


# ==============================================================================
# WebSocket Authentication Tests
# ==============================================================================

def test_ws_auth_header_valid(client):
    """Verify WebSocket authentication via 'Authorization: Bearer <token>' header."""
    mock_claims = {"uid": "ws_user_1", "email": "ws1@satyaswar.internal"}
    with patch("app.dependencies.auth.verify_id_token", return_value=mock_claims):
        with client.websocket_connect(
            "/api/v1/auth/ws-test",
            headers={"Authorization": "Bearer valid-ws-token"},
        ) as websocket:
            data = websocket.receive_json()
            assert data["type"] == "auth_success"
            assert data["uid"] == "ws_user_1"
            assert data["email"] == "ws1@satyaswar.internal"


def test_ws_auth_header_invalid(client):
    """Verify WebSocket connection is rejected (code 4401) when header token is invalid."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.InvalidIdTokenError("Invalid token"),
    ):
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/api/v1/auth/ws-test",
                headers={"Authorization": "Bearer bad-token"},
            ) as websocket:
                websocket.receive_json()


def test_ws_auth_first_message_valid(client):
    """Verify WebSocket authentication via first JSON message when header is absent."""
    mock_claims = {"uid": "ws_user_2", "email": "ws2@satyaswar.internal"}
    with patch("app.dependencies.auth.verify_id_token", return_value=mock_claims):
        with client.websocket_connect("/api/v1/auth/ws-test") as websocket:
            websocket.send_text(json.dumps({"type": "auth", "token": "valid-first-msg-token"}))
            data = websocket.receive_json()
            assert data["type"] == "auth_success"
            assert data["uid"] == "ws_user_2"
            assert data["email"] == "ws2@satyaswar.internal"


def test_ws_auth_first_message_invalid_token(client):
    """Verify WebSocket connection closes when first-message token is invalid."""
    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.InvalidIdTokenError("Invalid token"),
    ):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/auth/ws-test") as websocket:
                websocket.send_text(json.dumps({"type": "auth", "token": "bad-token"}))
                websocket.receive_json()


def test_ws_auth_first_message_wrong_type(client):
    """Verify WebSocket connection closes when first message is not an auth message."""
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/auth/ws-test") as websocket:
            websocket.send_text(json.dumps({"type": "not_auth", "data": "dummy"}))
            websocket.receive_json()


def test_ws_auth_timeout(client):
    """Verify WebSocket connection closes when first message times out."""
    with patch("app.dependencies.auth.WS_AUTH_TIMEOUT_SECONDS", 0.05):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/auth/ws-test") as websocket:
                # Do not send any message; timeout will trigger
                websocket.receive_json()


# ==============================================================================
# Helper & Singleton Tests
# ==============================================================================

def test_authenticate_ws_token_helper():
    """Verify authenticate_ws_token returns AuthUser on success and None on failure."""
    assert authenticate_ws_token(None) is None
    assert authenticate_ws_token("") is None

    mock_claims = {"uid": "helper_uid", "email": "helper@test.com"}
    with patch("app.dependencies.auth.verify_id_token", return_value=mock_claims):
        user = authenticate_ws_token("valid")
        assert user is not None
        assert user.uid == "helper_uid"

    with patch(
        "app.dependencies.auth.verify_id_token",
        side_effect=fb_auth.InvalidIdTokenError("Invalid"),
    ):
        assert authenticate_ws_token("invalid") is None


def test_firebase_init_duplicate_calls():
    """Verify that calling init_firebase multiple times does not raise duplicate app error."""
    app1 = init_firebase()
    app2 = init_firebase()
    assert app1 is app2

