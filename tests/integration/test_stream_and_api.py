"""
Integration tests for SatyaSwar ML engine, REST API, streaming, and mock mode.
Authoritative source: Implementation.md, Section 6.5, 6.6, 6.7, 15.3
"""

import struct
import time

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from satyaswar_ml.adapters.mock import MockCallSession
from satyaswar_ml.adapters.ws_app import app
from satyaswar_ml.audio.io import float32_to_pcm16le
from satyaswar_ml.engine import AnalysisEngine, SessionConfig
from satyaswar_ml.schemas import (
    CallSummaryEvent,
    Contact,
    ScoreEvent,
    SessionReadyEvent,
)


@pytest.mark.asyncio
class TestRestEndpoints:
    async def test_get_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ml/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["model_loaded"] is True
            assert "versions" in data
            assert "satyaswar_ml" in data["versions"]

    async def test_get_model_info(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ml/model-info")
            assert resp.status_code == 200
            data = resp.json()
            assert "model_name" in data
            assert "thresholds" in data

    async def test_post_contacts_match(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "text": "Hi, this is Priyanka calling",
                "contacts": [
                    {
                        "contact_id": "c1",
                        "display_name": "Priyanka Sharma",
                        "aliases": ["Priti"],
                    }
                ],
            }
            resp = await client.post("/ml/contacts/match", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["no_match"] is False
            assert len(data["candidates"]) >= 1


@pytest.mark.asyncio
class TestInProcessEngineStreaming:
    async def test_end_to_end_streaming_and_summary(self, tmp_path):
        engine = AnalysisEngine.from_config()
        await engine.warmup()

        contacts = [
            Contact(contact_id="uid_1", display_name="Priyanka Sharma", aliases=["Priti"]),
        ]
        session, ready_ev = engine.start_session(
            call_id="call_test_01",
            config=SessionConfig(mode="chunks", telephony_profile="none"),
            contacts=contacts,
        )
        assert isinstance(ready_ev, SessionReadyEvent)

        # Generate 4 chunks of 1.75s (7.0 seconds of audio)
        chunk_samples = 28000
        all_events = []

        for seq in range(4):
            # Synthetic 400 Hz tone + slight noise
            t = np.linspace(0, 1.75, chunk_samples, dtype=np.float32)
            audio = 0.5 * np.sin(2 * np.pi * 400 * t) + 0.01 * np.random.normal(0, 1, chunk_samples).astype(np.float32)
            pcm_bytes = float32_to_pcm16le(audio)

            # Build 12-byte header: uint32 seq, uint64 client_ts_ms
            client_ts_ms = int(time.time() * 1000)
            header = struct.pack("<IQ", seq, client_ts_ms)
            frame = header + pcm_bytes

            evs = await session.push_audio(frame)
            all_events.extend(evs)

        # Verify score events received
        scores = [e for e in all_events if isinstance(e, ScoreEvent)]
        assert len(scores) >= 1

        for sc in scores:
            assert sc.schema_version == "1.0"
            assert sc.band in ("low", "medium", "high", "insufficient")
            assert sc.outcome in ("likely_genuine", "suspicious", "insufficient_evidence")
            assert sc.latency_ms.total > 0.0

            # Critical requirement: distinguish synthetic from replay
            assert sc.evidence.synthetic_score is not None or sc.evidence.quality_label == "poor"

        # End session
        summary = await session.end()
        assert isinstance(summary, CallSummaryEvent)
        assert summary.call_id == "call_test_01"
        assert summary.windows_scored + summary.windows_insufficient == len(scores)

        # Privacy verification: assert audio ring buffers are completely emptied
        assert session.emitter.ring_buffer.total_samples_written == 0

    async def test_privacy_zero_disk_writes_during_call(self, tmp_path, monkeypatch):
        """
        Critical Requirement 4 & Section 14:
        Ensure no raw audio or transcripts are persisted to disk or log files.
        """
        monkeypatch.chdir(tmp_path)
        engine = AnalysisEngine.from_config()

        session, _ = engine.start_session("privacy_check_call")
        # Stream 3.5s audio
        audio = 0.3 * np.ones(56000, dtype=np.float32)
        pcm = float32_to_pcm16le(audio)
        header = struct.pack("<IQ", 0, int(time.time() * 1000))
        await session.push_audio(header + pcm)
        await session.end()

        # Check for any unexpected WAV or transcript dumps in current directory
        created_files = list(tmp_path.glob("**/*.*"))
        assert len(created_files) == 0, f"Privacy violation: unexpected files written: {created_files}"

    async def test_reconnect_resumes_session(self):
        engine = AnalysisEngine.from_config()
        session1, ready1 = engine.start_session("reconnect_call_id")

        # Reconnect with resume=True
        session2, ready2 = engine.start_session("reconnect_call_id", resume=True)
        assert session1 is session2

    async def test_mock_mode_marks_all_events(self):
        mock_session = MockCallSession(call_id="mock_test_call", scenario_id="clone_hi_01")
        # Push 2 chunks
        pcm = float32_to_pcm16le(np.zeros(28000, dtype=np.float32))
        evs1 = await mock_session.push_audio(pcm)
        evs2 = await mock_session.push_audio(pcm)
        all_evs = evs1 + evs2

        assert len(all_evs) >= 2
        for ev in all_evs:
            if hasattr(ev, "mock"):
                assert ev.mock is True, "Mock mode failed to set mock=true flag!"

        summary = await mock_session.end()
        assert summary.mock is True

    async def test_invalid_short_frame_emits_error(self):
        engine = AnalysisEngine.from_config()
        session, _ = engine.start_session("invalid_frame_call")
        # Only 6 bytes (less than 12-byte header)
        evs = await session.push_audio(b"123456")
        assert len(evs) == 1
        assert evs[0].type == "error"
        assert evs[0].code == "invalid_frame_header"

        assert evs[0].recoverable is True

    async def test_backpressure_window_dropping(self):
        engine = AnalysisEngine.from_config()
        # Session with max_pending_windows = 2
        session, _ = engine.start_session("backpressure_call")
        session.config.max_pending_windows = 1

        # Push 7 seconds of audio in one burst (multiple windows ready at once)
        chunk_samples = 28000 * 4
        pcm = float32_to_pcm16le(np.zeros(chunk_samples, dtype=np.float32))
        header = struct.pack("<IQ", 1, int(time.time() * 1000))
        evs = await session.push_audio(header + pcm)

        # Check for windows_dropped info event
        info_evs = [e for e in evs if (getattr(e, "type", None) == "info" or getattr(e, "event", None) == "info") and e.code == "windows_dropped"]
        assert len(info_evs) >= 1
        assert "Dropped" in info_evs[0].message

