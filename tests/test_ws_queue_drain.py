"""
SatyaSwar - Issue 2 Regression Test Suite
WebSocket Queue Draining, Lifecycle, and Finalization Tests
"""

import asyncio
import struct
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.dependencies.auth import AuthUser
from app.main import app
from app.models.enums import FinalOutcome, RiskLevel, SessionStatus
from app.repositories import calls as calls_repo
from app.services.ml_service import MLClient
from app.websocket.audio_frame import EXPECTED_PCM_BYTES
from tests.mock_firestore import MockFirestoreClient

USER_ID = "user_issue2_tester"


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_db = MockFirestoreClient()
    with patch("app.services.firebase.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.calls.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.verification.get_firestore_client", return_value=mock_db):
        yield mock_db


@pytest.fixture
def client():
    return TestClient(app)


def mock_verify_token(token: str):
    return AuthUser(uid=USER_ID, email=f"{USER_ID}@example.com", name="Tester")


def make_auth_headers():
    return {"Authorization": "Bearer mock_valid_token"}


def create_frame_m1(seq: int, offset_ms: int = 0, is_last: bool = False) -> bytes:
    """Builds a Member 1 20-byte LE header + 112,000 bytes PCM frame."""
    header = struct.pack(
        "<BBHIIQ",
        1,  # version
        1 if is_last else 0,  # flags (is_last)
        0,  # reserved
        seq,  # seq
        offset_ms,  # offset_ms
        int(time.time() * 1000),  # send_epoch_ms
    )
    return header + (b"\x00" * EXPECTED_PCM_BYTES)


def test_1_normal_final_audio_frame_with_multiple_queued_windows(client):
    """
    Test 1: Normal final audio frame with multiple queued windows.
    Frames seq=0, seq=1, seq=2 (is_last=True) are sent.
    All queued frames must be fully processed before outcome is emitted.
    """
    session = calls_repo.create_session("sess_issue2_drain_final_frame", USER_ID)
    processed_windows = []

    async def delayed_score(self, session_id, window_id, pcm_bytes):
        await asyncio.sleep(0.04)  # Simulate processing delay so frames queue up
        processed_windows.append(window_id)
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.15,
            "evidence_quality": 0.90,
            "speech_duration": 3.5,
            "processing_time_ms": 40,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", delayed_score):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            ready = ws.receive_json()
            assert ready["type"] == "connection_ready"

            # Send 3 frames rapidly, the 3rd having is_last=True
            ws.send_bytes(create_frame_m1(seq=0, offset_ms=0, is_last=False))
            ws.send_bytes(create_frame_m1(seq=1, offset_ms=1750, is_last=False))
            ws.send_bytes(create_frame_m1(seq=2, offset_ms=3500, is_last=True))

            # Receive messages
            messages = []
            while True:
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg.get("type") == "outcome":
                        break
                except Exception:
                    break

            # Verify all 3 frames scored
            score_messages = [m for m in messages if m.get("type") == "score"]
            assert len(score_messages) == 3
            assert [m["seq"] for m in score_messages] == [0, 1, 2]
            assert processed_windows == [0, 1, 2]

            # Verify outcome received after scores
            outcome_messages = [m for m in messages if m.get("type") == "outcome"]
            assert len(outcome_messages) == 1
            assert outcome_messages[0]["finalOutcome"] == "likely_genuine"


def test_2_explicit_end_message_with_queued_windows(client):
    """
    Test 2: Explicit end message with queued windows.
    Client sends seq=0, seq=1, then immediately text {"type": "end"}.
    Both windows must be drained and scored before outcome is sent.
    """
    session = calls_repo.create_session("sess_issue2_drain_explicit_end", USER_ID)
    processed_windows = []

    async def delayed_score(self, session_id, window_id, pcm_bytes):
        await asyncio.sleep(0.04)
        processed_windows.append(window_id)
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.20,
            "evidence_quality": 0.85,
            "speech_duration": 3.5,
            "processing_time_ms": 40,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", delayed_score):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            ready = ws.receive_json()
            assert ready["type"] == "connection_ready"

            ws.send_bytes(create_frame_m1(seq=0, offset_ms=0))
            ws.send_bytes(create_frame_m1(seq=1, offset_ms=1750))
            ws.send_json({"type": "end"})

            messages = []
            while True:
                try:
                    msg = ws.receive_json()
                    messages.append(msg)
                    if msg.get("type") == "outcome":
                        break
                except Exception:
                    break

            scores = [m for m in messages if m.get("type") == "score"]
            assert len(scores) == 2
            assert [m["seq"] for m in scores] == [0, 1]
            assert processed_windows == [0, 1]

            outcomes = [m for m in messages if m.get("type") == "outcome"]
            assert len(outcomes) == 1


def test_3_client_disconnect_while_windows_remain_queued(client):
    """
    Test 3: Client disconnect while windows remain queued.
    Server must drain the queued windows and record them in Firestore session.
    """
    session = calls_repo.create_session("sess_issue2_client_disconnect", USER_ID)
    processed_windows = []

    async def delayed_score(self, session_id, window_id, pcm_bytes):
        await asyncio.sleep(0.03)
        processed_windows.append(window_id)
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.10,
            "evidence_quality": 0.90,
            "speech_duration": 3.5,
            "processing_time_ms": 30,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", delayed_score):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            _ = ws.receive_json()  # connection_ready

            # Send frames and close the websocket client immediately
            ws.send_bytes(create_frame_m1(seq=0))
            ws.send_bytes(create_frame_m1(seq=1))
            ws.close()

            # Allow server-side ASGI lifecycle to drain the queue before test session cancels the scope
            time.sleep(0.2)

    assert 0 in processed_windows
    assert 1 in processed_windows

    # Verify session risk was persisted in DB
    updated = calls_repo.get_owned_session(session.session_id, USER_ID)
    assert updated.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert updated.window_count == 2


def test_4_ml_timeout_while_draining(client):
    """
    Test 4: ML timeout while draining.
    If the worker is blocked or takes longer than DRAIN_TIMEOUT_SECONDS,
    the coordinator times out, cancels the worker, and finalizes safely.
    """
    session = calls_repo.create_session("sess_issue2_drain_timeout", USER_ID)

    async def hanging_score(self, session_id, window_id, pcm_bytes):
        await asyncio.sleep(5.0)  # Hang longer than test drain timeout
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.10,
            "evidence_quality": 0.90,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", hanging_score), \
         patch("app.websocket.call_stream.DRAIN_TIMEOUT_SECONDS", 0.1):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            _ = ws.receive_json()  # connection_ready
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            # Must receive outcome despite timeout during drain
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"


def test_5_heartbeat_timeout(client):
    """
    Test 5: Heartbeat timeout.
    When client remains completely inactive exceeding HEARTBEAT_TIMEOUT_SECONDS,
    connection is terminated with HEARTBEAT_TIMEOUT error and code 4408.
    """
    session = calls_repo.create_session("sess_issue2_heartbeat", USER_ID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch("app.websocket.call_stream.HEARTBEAT_TIMEOUT_SECONDS", 0.1):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            _ = ws.receive_json()  # connection_ready

            # Wait for heartbeat timeout to fire
            err_msg = ws.receive_json()
            assert err_msg["type"] == "error"
            assert err_msg["code"] == "HEARTBEAT_TIMEOUT"
            assert err_msg["fatal"] is True


def test_6_worker_exception_marks_analysis_unavailable(client):
    """
    Test 6: Worker exception.
    When worker encounters an unexpected fatal exception, it does not crash silently;
    final outcome is marked as 'unavailable'.
    """
    session = calls_repo.create_session("sess_issue2_worker_exception", USER_ID)

    async def crashing_score(self, session_id, window_id, pcm_bytes):
        raise RuntimeError("Fatal internal ML worker crash")

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", crashing_score):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            _ = ws.receive_json()  # connection_ready
            ws.send_bytes(create_frame_m1(seq=0, is_last=True))

            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            # Since worker crashed, analysis is marked unavailable
            assert outcome["finalOutcome"] == FinalOutcome.UNAVAILABLE.value
            assert "unavailable" in outcome["headline"].lower()


def test_7_empty_audio_queue(client):
    """
    Test 7: Empty audio queue.
    Client connects and immediately sends 'end' without sending any audio frames.
    Lifecycle must complete cleanly and return outcome without error.
    """
    session = calls_repo.create_session("sess_issue2_empty_queue", USER_ID)

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token):
        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            ready = ws.receive_json()
            assert ready["type"] == "connection_ready"

            ws.send_json({"type": "end"})
            outcome = ws.receive_json()
            assert outcome["type"] == "outcome"
            assert outcome["finalOutcome"] == FinalOutcome.UNAVAILABLE.value


def test_8_exactly_one_final_outcome(client):
    """
    Test 8: Exactly one final outcome.
    Ensures that under standard or edge-case termination, outcome is emitted
    strictly once, preventing duplicate history records or duplicate broadcasts.
    """
    session = calls_repo.create_session("sess_issue2_single_outcome", USER_ID)

    async def mock_score(self, session_id, window_id, pcm_bytes):
        return {
            "session_id": session_id,
            "window_id": window_id,
            "spoof_score": 0.15,
            "evidence_quality": 0.90,
        }

    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         patch.object(MLClient, "score_window", mock_score):

        with client.websocket_connect(
            f"/ws/v1/calls/{session.session_id}",
            headers=make_auth_headers(),
        ) as ws:
            _ = ws.receive_json()  # connection_ready

            ws.send_bytes(create_frame_m1(seq=0))
            _ = ws.receive_json()  # score

            # Send multiple end messages to stress finalization idempotency
            ws.send_json({"type": "end"})
            ws.send_json({"type": "end"})

            outcomes = []
            while True:
                try:
                    msg = ws.receive_json()
                    if msg.get("type") == "outcome":
                        outcomes.append(msg)
                except Exception:
                    break

            # Exactly one final outcome must have been broadcast
            assert len(outcomes) == 1
