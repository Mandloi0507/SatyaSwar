"""
SatyaSwar - Module 5 Automated Test Suite
WebSocket Audio Streaming & ML Service Integration Tests
"""

import asyncio
import struct
import time
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.enums import SessionStatus
from app.repositories import calls as calls_repo
from app.services.ml_service import MLClient, MLUnavailable
from app.websocket.audio_frame import EXPECTED_PCM_BYTES
from tests.mock_firestore import MockFirestoreClient
from tests.mock_ml_server import app as mock_ml_app, config as mock_ml_config, reset_mock_ml_config

USER_A_UID = "user_m5_alice"
USER_B_UID = "user_m5_bob"


@pytest.fixture(autouse=True)
def setup_mock_db_and_ml():
    """Reset mock firestore and mock ML configuration for each test."""
    mock_db = MockFirestoreClient()
    reset_mock_ml_config()
    with patch("app.repositories.calls.get_firestore_client", return_value=mock_db):
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


def create_test_frame_m1(seq: int, offset_ms: int = 0, is_last: bool = False, pcm_bytes: bytes = None) -> bytes:
    """Builds a Member 1 20-byte LE header + 112,000 bytes PCM frame."""
    if pcm_bytes is None:
        pcm_bytes = b"\x00" * EXPECTED_PCM_BYTES
    header = struct.pack(
        "<BBHIIQ",
        1,  # version
        1 if is_last else 0,  # flags (is_last)
        0,  # reserved
        seq,  # seq
        offset_ms,  # offset_ms
        int(time.time() * 1000),  # send_epoch_ms
    )
    return header + pcm_bytes


def create_test_frame_m2(seq: int, timestamp_ms: int = 0, pcm_bytes: bytes = None) -> bytes:
    """Builds a Member 2 12-byte BE header + 112,000 bytes PCM frame."""
    if pcm_bytes is None:
        pcm_bytes = b"\x00" * EXPECTED_PCM_BYTES
    header = struct.pack(">IQ", seq, timestamp_ms or int(time.time() * 1000))
    return header + pcm_bytes


def test_unauthenticated_socket_rejected(client):
    """WebSocket connection with missing/invalid auth must be rejected with code 4401."""
    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/v1/calls/test_sess_1", headers={"Authorization": "Bearer bad_token"}):
                pass
        assert exc_info.value.code == 4401


def test_foreign_session_socket_rejected(client):
    """User B attempting to connect to User A's session must be rejected with code 4404."""
    # Create session owned by User A
    session = calls_repo.create_session("sess_alice_01", USER_A_UID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_b = make_user_token(USER_B_UID)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"/ws/v1/calls/{session.session_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            ):
                pass
        assert exc_info.value.code == 4404


def test_nonexistent_session_socket_rejected(client):
    """Connecting to a non-existent session ID must be rejected with code 4404."""
    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/ws/v1/calls/does_not_exist",
                headers={"Authorization": f"Bearer {token_a}"},
            ):
                pass
        assert exc_info.value.code == 4404


def test_terminal_state_session_socket_rejected(client):
    """Connecting to a COMPLETED session must be rejected with code 4409 (Conflict)."""
    session = calls_repo.create_session("sess_completed", USER_A_UID)
    calls_repo.transition_session_status(
        session_id=session.session_id,
        user_id=USER_A_UID,
        new_status=SessionStatus.ACTIVE,
        allowed_from={SessionStatus.CREATED},
    )
    calls_repo.transition_session_status(
        session_id=session.session_id,
        user_id=USER_A_UID,
        new_status=SessionStatus.PROCESSING,
        allowed_from={SessionStatus.ACTIVE},
    )
    calls_repo.transition_session_status(
        session_id=session.session_id,
        user_id=USER_A_UID,
        new_status=SessionStatus.COMPLETED,
        allowed_from={SessionStatus.PROCESSING},
    )

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"/ws/v1/calls/{session.session_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            ):
                pass
        assert exc_info.value.code == 4409


def test_valid_connection_handshake_and_alias(client):
    """
    Connecting to an owned CREATED session transitions state to ACTIVE and
    emits 'connection_ready'. Both `/ws/v1/calls/{id}` and `/ws/call/{id}` must work.
    """
    session = calls_repo.create_session("sess_handshake", USER_A_UID)
    assert session.status == SessionStatus.CREATED

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        with client.websocket_connect(
            f"/ws/call/{session.session_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        ) as ws:
            ready_msg = ws.receive_json()
            assert ready_msg["type"] == "connection_ready"
            assert ready_msg["session_id"] == session.session_id
            assert ready_msg["config"]["sampleRate"] == 16000

        # Verify session is now ACTIVE in database
        updated = calls_repo.get_owned_session(session.session_id, USER_A_UID)
        assert updated.status == SessionStatus.ACTIVE


def test_ping_pong_and_hello_ack_control_messages(client):
    """Client sending ping/hello receives appropriate pong/hello_ack."""
    session = calls_repo.create_session("sess_control", USER_A_UID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        ) as ws:
            _ = ws.receive_json()  # connection_ready

            # Test hello
            ws.send_json({"type": "hello", "callId": session.session_id})
            hello_ack = ws.receive_json()
            assert hello_ack["type"] == "hello_ack"
            assert hello_ack["callId"] == session.session_id

            # Test ping
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert pong["session_id"] == session.session_id


def test_invalid_frame_and_out_of_order_frame_handling(client):
    """Invalid frame sizes and out-of-order sequence numbers receive error events."""
    session = calls_repo.create_session("sess_invalid_frames", USER_A_UID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        token_a = make_user_token(USER_A_UID)
        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        ) as ws:
            _ = ws.receive_json()  # connection_ready

            # Send wrong size frame (e.g. 100 bytes)
            ws.send_bytes(b"\x00" * 100)
            err1 = ws.receive_json()
            assert err1["type"] == "error"
            assert err1["code"] == "INVALID_AUDIO_FRAME"

            # Send valid frame with seq=5
            frame_seq5 = create_test_frame_m1(seq=5)
            ws.send_bytes(frame_seq5)

            # Wait briefly for ML scoring or drain
            # Then send duplicate frame with seq=5 (should trigger sequence error)
            ws.send_bytes(frame_seq5)
            err2 = ws.receive_json()
            # It could be score message first or error
            if err2.get("type") == "score":
                err2 = ws.receive_json()
            assert err2["type"] == "error"
            assert err2["code"] == "INVALID_AUDIO_FRAME"


def test_streaming_audio_frames_and_score_broadcast(client):
    """
    Streaming Member 1 and Member 2 formatted frames produces real-time scores
    matching Member 1's expected schema and updates rolling risk.
    """
    session = calls_repo.create_session("sess_streaming", USER_A_UID)

    # Mock ML client to return deterministic scores without external network
    async def mock_score_window(self, session_id, window_id, pcm_bytes):
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.88,
            "evidence_quality": 0.92,
            "speech_duration": 3.5,
            "processing_time_ms": 110,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        with patch.object(MLClient, "score_window", mock_score_window):
            token_a = make_user_token(USER_A_UID)
            with client.websocket_connect(
                f"/ws/v1/calls/{session.session_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            ) as ws:
                ready = ws.receive_json()
                assert ready["type"] == "connection_ready"

                # Send Member 1 frame (seq 0)
                frame0 = create_test_frame_m1(seq=0, offset_ms=0)
                ws.send_bytes(frame0)

                score0 = ws.receive_json()
                assert score0["type"] == "score"
                assert score0["seq"] == 0
                assert score0["windowRiskIndex"] == 88
                assert score0["call"]["band"] == "high"
                assert score0["voiceOutcome"] == "suspicious"
                assert score0["evidence"]["level"] == "good"

                # Send Member 2 frame (seq 1) with is_last simulated via text end
                frame1 = create_test_frame_m2(seq=1, timestamp_ms=1750)
                ws.send_bytes(frame1)

                score1 = ws.receive_json()
                assert score1["type"] == "score"
                assert score1["seq"] == 1
                assert score1["call"]["riskIndex"] >= 80

                # End call and verify outcome message
                ws.send_json({"type": "end"})
                outcome = ws.receive_json()
                assert outcome["type"] == "outcome"
                assert outcome["finalOutcome"] == "likely_impersonation"


def test_ml_service_consecutive_failures_broadcasts_unavailable(client):
    """When ML service experiences consecutive failures, analysis_unavailable is broadcast."""
    session = calls_repo.create_session("sess_ml_fail", USER_A_UID)

    async def mock_failing_score(self, session_id, window_id, pcm_bytes):
        raise MLUnavailable("Simulated upstream model timeout")

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        with patch.object(MLClient, "score_window", mock_failing_score):
            token_a = make_user_token(USER_A_UID)
            with client.websocket_connect(
                f"/ws/v1/calls/{session.session_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            ) as ws:
                _ = ws.receive_json()  # connection_ready

                # Send 3 frames to trigger 3 failures
                ws.send_bytes(create_test_frame_m1(seq=0))
                ws.send_bytes(create_test_frame_m1(seq=1))
                ws.send_bytes(create_test_frame_m1(seq=2))

                unavailable_msg = ws.receive_json()
                assert unavailable_msg["type"] == "analysis_unavailable"
                assert unavailable_msg["code"] == "ML_SERVICE_UNAVAILABLE"


def test_session_isolation(client):
    """Scores broadcast on Session A must never leak to Session B."""
    session_a = calls_repo.create_session("sess_iso_a", USER_A_UID)
    session_b = calls_repo.create_session("sess_iso_b", USER_B_UID)

    async def mock_score_window(self, session_id, window_id, pcm_bytes):
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.25 if session_id == "sess_iso_b" else 0.90,
            "evidence_quality": 0.85,
            "speech_duration": 3.5,
            "processing_time_ms": 50,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        with patch.object(MLClient, "score_window", mock_score_window):
            token_a = make_user_token(USER_A_UID)
            token_b = make_user_token(USER_B_UID)

            with client.websocket_connect(
                f"/ws/v1/calls/{session_a.session_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            ) as ws_a, client.websocket_connect(
                f"/ws/v1/calls/{session_b.session_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            ) as ws_b:
                _ = ws_a.receive_json()  # ready
                _ = ws_b.receive_json()  # ready

                # Stream to A only
                ws_a.send_bytes(create_test_frame_m1(seq=0))
                msg_a = ws_a.receive_json()
                assert msg_a["type"] == "score"
                assert msg_a["windowRiskIndex"] == 90

                # Verify B can send ping and only receives pong, NOT A's score
                ws_b.send_json({"type": "ping"})
                msg_b = ws_b.receive_json()
                assert msg_b["type"] == "pong"
                assert msg_b["session_id"] == session_b.session_id
