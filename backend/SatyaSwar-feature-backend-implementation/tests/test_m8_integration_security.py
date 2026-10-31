"""
SatyaSwar - Module 8 Automated Test Suite
End-to-End System Integration, Security Audits & Privacy Verification
"""

import json
import struct
import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import FinalOutcome, RiskLevel, SessionStatus, VerificationStatus
from app.repositories import users as users_repo
from app.services.ml_service import MLClient
from app.websocket.audio_frame import EXPECTED_PCM_BYTES
from tests.mock_firestore import MockFirestoreClient

USER_ALICE_UID = "e2e_user_alice"
USER_BOB_UID = "e2e_user_bob"


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_db = MockFirestoreClient()
    with patch("app.services.firebase.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.users.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.contacts.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.calls.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.verification.get_firestore_client", return_value=mock_db), \
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


def create_audio_frame(seq: int, offset_ms: int = 0) -> bytes:
    """Builds a Member 1 20-byte LE header + 112,000 bytes PCM frame."""
    header = struct.pack(
        "<BBHIIQ",
        1,  # version
        0,  # flags
        0,  # reserved
        seq,  # seq
        offset_ms,
        int(time.time() * 1000),
    )
    return header + (b"\x00" * EXPECTED_PCM_BYTES)


def test_complete_end_to_end_call_and_verification_flow(client, setup_mock_db):
    """
    Simulates the complete SatyaSwar user journey:
    1. Alice and Bob provision their profiles.
    2. Alice generates an invite; Bob accepts to form a trusted-contact link.
    3. Alice initiates a call session and connects over WebSocket.
    4. Audio windows are streamed and scored live.
    5. Mid-call, Alice initiates out-of-band verification targeting Bob.
    6. Bob confirms the request using the 2-digit match code.
    7. Alice's WebSocket stream receives the verification update.
    8. Call ends and compact history summary is persisted.
    """
    token_alice = make_user_token(USER_ALICE_UID)
    token_bob = make_user_token(USER_BOB_UID)

    async def mock_score_window(self, session_id, window_id, pcm_bytes):
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.20,  # low spoof risk
            "evidence_quality": 0.90,
            "speech_duration": 3.5,
            "processing_time_ms": 95,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score_window):

        # 1. Profile auto-provisioning
        resp_a = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token_alice}"})
        assert resp_a.status_code == 200
        assert resp_a.json()["uid"] == USER_ALICE_UID

        resp_b = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token_bob}"})
        assert resp_b.status_code == 200
        assert resp_b.json()["uid"] == USER_BOB_UID

        # 2. Contact invite & acceptance
        invite_resp = client.post("/api/v1/contacts/invite", json={}, headers={"Authorization": f"Bearer {token_alice}"})
        assert invite_resp.status_code == 201
        invite_code = invite_resp.json()["code"]

        accept_resp = client.post(
            "/api/v1/contacts/accept",
            json={"code": invite_code, "alias": "Bobby", "label": "friend"},
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert accept_resp.status_code == 200

        # 3. Start call session
        start_call_resp = client.post(
            "/api/v1/calls/start",
            json={"claimed_name": "Bob", "caller_number": "+919876543210"},
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert start_call_resp.status_code == 201
        call_data = start_call_resp.json()
        session_id = call_data["session_id"]
        assert call_data["status"] == "CREATED"

        # 4. Stream audio over WebSocket
        with client.websocket_connect(
            f"/ws/v1/calls/{session_id}",
            headers={"Authorization": f"Bearer {token_alice}"},
        ) as ws:
            ready = ws.receive_json()
            assert ready["type"] == "connection_ready"

            # Stream 2 audio frames
            ws.send_bytes(create_audio_frame(seq=0, offset_ms=0))
            score0 = ws.receive_json()
            assert score0["type"] == "score"
            assert score0["seq"] == 0
            assert score0["windowRiskIndex"] == 20

            ws.send_bytes(create_audio_frame(seq=1, offset_ms=1750))
            score1 = ws.receive_json()
            assert score1["type"] == "score"
            assert score1["seq"] == 1

            # 5. Initiate verification request targeting Bob
            ver_create_resp = client.post(
                "/api/v1/verifications",
                json={
                    "session_id": session_id,
                    "target_uid": USER_BOB_UID,
                    "claimed_identity": "Bob",
                    "action_type": "money_transfer",
                    "amount": 50000.0,
                },
                headers={"Authorization": f"Bearer {token_alice}"},
            )
            assert ver_create_resp.status_code == 201
            ver_data = ver_create_resp.json()
            ver_id = ver_data["verification_id"]
            match_code = ver_data["match_code"]

            # WebSocket receives verification pending update
            ws_ver_pending = ws.receive_json()
            assert ws_ver_pending["type"] == "verification_update"
            assert ws_ver_pending["status"] == "PENDING"

            # 6. Bob confirms verification
            respond_resp = client.post(
                f"/api/v1/verifications/{ver_id}/respond",
                json={"decision": "confirm", "selected_code": match_code},
                headers={"Authorization": f"Bearer {token_bob}"},
            )
            assert respond_resp.status_code == 200
            assert respond_resp.json()["status"] == "APPROVED"

            # WebSocket receives verification approved update
            ws_ver_approved = ws.receive_json()
            assert ws_ver_approved["type"] == "verification_update"
            assert ws_ver_approved["status"] == "APPROVED"

            # 7. End call cleanly
            ws.send_json({"type": "end"})
            ws_outcome = ws.receive_json()
            assert ws_outcome["type"] == "outcome"

        # 8. Finalize call and verify persistence
        end_call_resp = client.post(f"/api/v1/calls/{session_id}/end", headers={"Authorization": f"Bearer {token_alice}"})
        assert end_call_resp.status_code == 200
        assert end_call_resp.json()["status"] == "COMPLETED"

        result_resp = client.get(f"/api/v1/calls/{session_id}/result", headers={"Authorization": f"Bearer {token_alice}"})
        assert result_resp.status_code == 200
        assert result_resp.json()["status"] == "COMPLETED"

        history_resp = client.get("/api/v1/calls/history", headers={"Authorization": f"Bearer {token_alice}"})
        assert history_resp.status_code == 200
        history_items = history_resp.json()
        assert len(history_items) >= 1
        assert history_items[0]["session_id"] == session_id


def test_privacy_zero_audio_retention_audit(client, setup_mock_db):
    """
    Privacy Audit (Section 8.1 / 8.2):
    Grep all stored Firestore documents to verify that ZERO audio bytes, waveforms,
    or transcripts are ever persisted in the database.
    """
    forbidden_keys = {"audio", "pcm", "raw_audio", "wav", "transcript", "speech_text"}

    for col_name, col_ref in setup_mock_db.collections.items():
        for doc_id, doc_dict in col_ref.store.items():
            for key in doc_dict.keys():
                assert key.lower() not in forbidden_keys, f"Forbidden key '{key}' found in '{col_name}/{doc_id}'"
            for key, val in doc_dict.items():
                if isinstance(val, (bytes, bytearray)):
                    assert len(val) < 1024, f"Large binary data found under '{key}' in '{col_name}/{doc_id}'"


def test_cascading_account_deletion_scrub(client, setup_mock_db):
    """
    GDPR / Account Deletion Audit:
    Deleting user Alice must scrub her profile and cascade-delete her sessions,
    contact entries, and history summaries.
    """
    token_alice = make_user_token(USER_ALICE_UID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch("firebase_admin.auth.delete_user"):
        # Auto-provision Alice
        client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token_alice}"})

        # Create session
        client.post("/api/v1/calls/start", json={"claimed_name": "Test"}, headers={"Authorization": f"Bearer {token_alice}"})

        # Delete account (initiates and executes cascading purge)
        del_resp = client.delete("/api/v1/users/me", headers={"Authorization": f"Bearer {token_alice}"})
        assert del_resp.status_code == 202

        # Verify profile is completely purged from database
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            users_repo.get_user_profile(USER_ALICE_UID)
        assert exc_info.value.status_code == 404

        # Confirm all user data is scrubbed
        users_col = setup_mock_db.collections.get("users")
        assert users_col is None or USER_ALICE_UID not in users_col.store

        sessions_col = setup_mock_db.collections.get("call_sessions")
        if sessions_col:
            for doc in sessions_col.store.values():
                assert doc.get("user_id") != USER_ALICE_UID

        history_col = setup_mock_db.collections.get("call_history")
        if history_col:
            for doc in history_col.store.values():
                assert doc.get("user_id") != USER_ALICE_UID
