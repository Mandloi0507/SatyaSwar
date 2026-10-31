"""
SatyaSwar End-to-End Real ML Integration Pipeline Test
Tests complete chain: Binary Audio Frame -> FastAPI WebSocket -> Real ML Service -> Live Risk Broadcast.
No mocks for ML: Uses the real ML inference engine running on http://127.0.0.1:8100.
"""

import os
import struct
import time
import wave
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import SessionStatus
from app.repositories import calls as calls_repo
from tests.mock_firestore import MockFirestoreClient

USER_ID = "user_e2e_tester"
USER_TOKEN = f"mock_token_{USER_ID}"
SESSION_ID = "session_e2e_real_ml_001"


def create_flutter_binary_frame(
    seq: int,
    offset_ms: int,
    pcm_bytes: bytes,
    is_last: bool = False,
) -> bytes:
    """
    Constructs a 20-byte LE header matching Flutter's AudioFrameBuilder (Strategy 1):
    - uint8 version (1)
    - uint8 flags (bit 0 = is_last)
    - uint16 reserved (0)
    - uint32 seq (LE)
    - uint32 offset_ms (LE)
    - uint64 send_epoch_ms (LE)
    Followed by 112,000 bytes PCM16 payload (total 112,020 bytes).
    """
    flags = 1 if is_last else 0
    now_ms = int(time.time() * 1000)
    header = struct.pack("<BBHIIQ", 1, flags, 0, seq, offset_ms, now_ms)
    assert len(header) == 20
    return header + pcm_bytes


@pytest.fixture(autouse=True)
def setup_mock_db():
    mock_db = MockFirestoreClient()
    with patch("app.services.firebase.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.calls.get_firestore_client", return_value=mock_db), \
         patch("app.repositories.verification.get_firestore_client", return_value=mock_db):
        yield mock_db


def mock_verify_token(token: str):
    from app.dependencies.auth import AuthUser
    from fastapi import HTTPException
    if not token or not token.startswith("mock_token_"):
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = token.replace("mock_token_", "")
    return AuthUser(uid=uid, email=f"{uid}@example.com", name=uid.capitalize())


def test_e2e_real_ml_audio_streaming():
    client = TestClient(app)

    # 1. Create a call session in the database
    calls_repo.create_session(SESSION_ID, USER_ID)

    # 2. Read real 112,000-byte PCM audio window from genuine/clone audio
    wav_path = r"C:\Users\Abhishek Shukla\Desktop\Final\frontend\SatyaSwar-mad\assets\audio\calls\clone_ceo_01.wav"
    assert os.path.isfile(wav_path), f"Audio fixture missing at {wav_path}"
    with wave.open(wav_path, "rb") as w:
        pcm_window = w.readframes(56000)
    assert len(pcm_window) == 112000, f"Expected 112000 PCM bytes, got {len(pcm_window)}"

    # 3. Connect via WebSocket passing token in query params (Flutter connection strategy)
    ws_url = f"/ws/call/{SESSION_ID}?token={USER_TOKEN}"
    with patch("app.dependencies.auth.verify_token", side_effect=mock_verify_token), \
         client.websocket_connect(ws_url) as ws:
        # Step A: Expect connection_ready acknowledgement
        ready_msg = ws.receive_json()
        assert ready_msg["type"] == "connection_ready"
        assert ready_msg["session_id"] == SESSION_ID
        assert ready_msg["config"]["windowMs"] == 3500

        # Step B: Send first real audio frame (seq = 0)
        frame_0 = create_flutter_binary_frame(seq=0, offset_ms=0, pcm_bytes=pcm_window, is_last=False)
        ws.send_bytes(frame_0)

        # Step C: Receive broadcast score message computed by REAL ML engine
        score_msg = ws.receive_json()
        assert score_msg["type"] == "score"
        assert score_msg["seq"] == 0
        assert score_msg["window_seq"] == 0

        # Verify score is genuine (not null, not negative, strictly bounded in [0.0, 100.0])
        assert "risk_score" in score_msg
        assert 0.0 <= score_msg["risk_score"] <= 100.0

        # Verify evidence quality reflects real speech
        assert "evidence_quality" in score_msg
        assert 0.0 <= score_msg["evidence_quality"] <= 1.0
        assert score_msg["evidence_quality"] >= 0.70  # Real speech clip has high evidence quality

        # Verify canonical band and latency keys
        assert score_msg["risk_band"] in ("low", "medium", "high", "insufficient")
        assert score_msg["band"] in ("low", "medium", "high", "insufficient")
        assert score_msg["latency_ms"] > 0

        # Step D: Send final frame (is_last = True) to trigger clean bounded drain
        frame_1 = create_flutter_binary_frame(seq=1, offset_ms=1750, pcm_bytes=pcm_window, is_last=True)
        ws.send_bytes(frame_1)

        # Receive second score event
        score_msg_2 = ws.receive_json()
        assert score_msg_2["type"] == "score"
        assert score_msg_2["seq"] == 1

        # Receive final outcome message
        final_msg = ws.receive_json()
        assert final_msg["type"] == "outcome"
        assert final_msg["session_id"] == SESSION_ID
        assert "finalOutcome" in final_msg
        assert final_msg["finalOutcome"] in ("likely_genuine", "suspicious", "insufficient_evidence", "inconclusive", "action_held", "verified_safe")
