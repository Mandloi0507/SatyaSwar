"""
Unit & Privacy tests for SatyaSwar Zero-Retention Audio and Log Sanitization.
Authoritative source: Master Prompt Critical Requirement 4 & Implementation.md Section 14.
"""

from pathlib import Path

import pytest

from satyaswar_ml.audio.windowing import RingBuffer
from satyaswar_ml.config import PrivacyConfig, SatyaSwarConfig
from satyaswar_ml.schemas import InfoEvent


def test_demo_environment_refuses_debug_audio_dump():
    """Verify demo mode strictly forbids debug audio dumping."""
    with pytest.raises(ValueError, match="demo environment strictly forbids debug_dump_audio"):
        SatyaSwarConfig(
            env="demo",
            privacy=PrivacyConfig(debug_dump_audio=True),
        )



def test_ring_buffer_zero_persistence_and_cleanup():
    """Verify in-memory ring buffer operates strictly in RAM and cleans up completely."""
    rb = RingBuffer(capacity_samples=16000 * 8)
    import numpy as np
    data = np.random.randn(16000 * 3).astype(np.float32)
    rb.append(data)
    assert rb.total_samples_written == 16000 * 3

    # Clean up
    rb.clear()
    assert rb.total_samples_written == 0
    # No temporary files created
    assert not Path("temp_buffer.raw").exists()



def test_event_log_sanitization_no_pii():
    """Verify score and info events contain only metadata and no raw audio or transcripts."""
    info = InfoEvent(
        call_id="call_999",
        code="windows_dropped",
        message="Dropped oldest windows under backpressure",
    )
    dump = info.model_dump_json()
    assert "audio" not in dump
    assert "transcript" not in dump
    assert "call_999" in dump


def test_zero_raw_audio_on_disk_check(tmp_path):
    """Scan workspace for unexpected .wav/.pcm dumps."""
    root_dir = Path(__file__).parent.parent.parent
    # Scan for any leaked audio dumps created during test runs (excluding intentional fixtures)
    suspicious = list(root_dir.glob("ml_dump_*.wav")) + list(root_dir.glob("*.pcm"))
    assert len(suspicious) == 0, f"Found leaked raw audio on disk: {suspicious}"
