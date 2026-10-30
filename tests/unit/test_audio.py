"""
Unit tests for audio I/O, windowing, and telephony simulation.
Authoritative source: Implementation.md, Section 7.1, 7.2, 7.10, 15.1
"""

import numpy as np
import pytest

from satyaswar_ml.audio.io import (
    float32_to_pcm16le,
    pcm16le_to_float32,
    resample_audio,
)
from satyaswar_ml.audio.telephony import (
    apply_g711_alaw,
    apply_g711_ulaw,
    apply_telephony_profile,
)
from satyaswar_ml.audio.windowing import (
    RingBuffer,
    WindowEmitter,
    prepare_model_input,
)


class TestAudioIO:
    def test_pcm16_roundtrip_fidelity(self):
        # Generate 16 kHz tone in [-1.0, 1.0]
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        orig = 0.8 * np.sin(2 * np.pi * 440 * t)

        raw_bytes = float32_to_pcm16le(orig)
        assert len(raw_bytes) == 32000

        reconstructed = pcm16le_to_float32(raw_bytes)
        assert len(reconstructed) == len(orig)
        # Quantization error for 16-bit is < 1e-4
        np.testing.assert_allclose(orig, reconstructed, atol=1e-4)

    def test_pcm16_odd_byte_count_rejected(self):
        with pytest.raises(ValueError, match="not a multiple of 2"):
            pcm16le_to_float32(b"\x00\x01\x02")

    def test_pcm16_empty_bytes(self):
        assert len(pcm16le_to_float32(b"")) == 0
        assert float32_to_pcm16le(np.empty(0, dtype=np.float32)) == b""

    def test_resample_audio(self):
        # 8 kHz sine wave resampled to 16 kHz
        t = np.linspace(0, 1.0, 8000, endpoint=False, dtype=np.float32)
        sine_8k = np.sin(2 * np.pi * 300 * t)

        resampled = resample_audio(sine_8k, orig_sr=8000, target_sr=16000)
        assert len(resampled) == 16000


class TestRingBuffer:
    def test_ring_buffer_retention_and_ordering(self):
        buf = RingBuffer(capacity_samples=10)

        # Ingest 6 samples
        buf.append(np.array([1, 2, 3, 4, 5, 6], dtype=np.float32))
        latest = buf.get_latest(4)
        np.testing.assert_array_equal(latest, [3, 4, 5, 6])

        # Overwrite with 8 more samples (exceeds capacity, should wrap)
        buf.append(np.array([7, 8, 9, 10, 11, 12, 13, 14], dtype=np.float32))
        latest = buf.get_latest(5)
        np.testing.assert_array_equal(latest, [10, 11, 12, 13, 14])


class TestWindowEmitter:
    def test_chunk_mode_hop_and_window_timing(self):
        emitter = WindowEmitter(sample_rate=16000, window_s=3.5, hop_s=1.75, mode="chunks")
        chunk_samples = 28000  # 1.75 s

        # Chunk 1 (0 to 1.75s): not enough for 3.5s window -> 0 windows
        w1 = emitter.push(np.ones(chunk_samples, dtype=np.float32))
        assert len(w1) == 0

        # Chunk 2 (1.75 to 3.5s): reaches 3.5s -> first window emitted
        w2 = emitter.push(np.ones(chunk_samples, dtype=np.float32))
        assert len(w2) == 1
        assert w2[0].index == 0
        assert w2[0].start_ms == 0
        assert w2[0].end_ms == 3500
        assert len(w2[0].audio) == 56000

        # Chunk 3 (3.5 to 5.25s): next hop -> second window emitted
        w3 = emitter.push(np.ones(chunk_samples, dtype=np.float32))
        assert len(w3) == 1
        assert w3[0].index == 1
        assert w3[0].start_ms == 1750
        assert w3[0].end_ms == 5250
        assert len(w3[0].audio) == 56000

    def test_end_of_call_flush(self):
        emitter = WindowEmitter(sample_rate=16000, window_s=3.5, hop_s=1.75, mode="chunks")
        # Ingest 3.5s (window 0)
        emitter.push(np.ones(56000, dtype=np.float32))
        # Ingest 1.625s (26,000 samples) unscored audio (< 28,000 hop, but > 24,000 min_unscored_s)
        emitter.push(np.ones(26000, dtype=np.float32))

        flushed = emitter.flush(min_unscored_s=1.5)
        assert flushed is not None
        assert flushed.is_final is True
        assert len(flushed.audio) == 56000

    def test_short_call_flush_ignored_if_under_min_speech(self):
        emitter = WindowEmitter(sample_rate=16000, window_s=3.5, hop_s=1.75, mode="chunks")
        # Only 1.0s audio ingested (< 1.5s minimum)
        emitter.push(np.ones(16000, dtype=np.float32))
        flushed = emitter.flush(min_unscored_s=1.5)
        assert flushed is None


class TestModelInputPreparation:
    def test_repeat_padding_to_64600(self):
        audio_56k = np.ones(56000, dtype=np.float32)
        prepared = prepare_model_input(audio_56k, target_samples=64600, pad_mode="repeat")
        assert len(prepared) == 64600
        # Verify first part is original and trailing is tiled
        np.testing.assert_array_equal(prepared[:56000], audio_56k)
        np.testing.assert_array_equal(prepared[56000:], audio_56k[:8600])

    def test_zero_padding_to_64600(self):
        audio_56k = np.ones(56000, dtype=np.float32)
        prepared = prepare_model_input(audio_56k, target_samples=64600, pad_mode="zeros")
        assert len(prepared) == 64600
        assert np.all(prepared[56000:] == 0.0)


class TestTelephonySimulation:
    def test_g711_output_length_preserved(self):
        audio = np.random.uniform(-0.5, 0.5, 56000).astype(np.float32)
        out_ulaw = apply_g711_ulaw(audio)
        out_alaw = apply_g711_alaw(audio)
        assert len(out_ulaw) == len(audio)
        assert len(out_alaw) == len(audio)

    def test_g711_bandlimiting_energy_drop_above_4khz(self):
        """High frequency tone (6 kHz) must be attenuated through 8 kHz companded channel."""
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        sine_6khz = np.sin(2 * np.pi * 6000 * t).astype(np.float32)

        filtered = apply_g711_ulaw(sine_6khz)
        orig_power = np.mean(sine_6khz**2)
        filtered_power = np.mean(filtered**2)

        # 6 kHz is above Nyquist (4 kHz) of an 8 kHz telephone channel, so energy drops dramatically
        assert filtered_power < 0.05 * orig_power

    def test_telephony_profiles_dispatch(self):
        audio = np.ones(16000, dtype=np.float32)
        out_none = apply_telephony_profile(audio, "none")
        np.testing.assert_array_equal(out_none, audio)

        out_ulaw = apply_telephony_profile(audio, "g711_ulaw")
        assert len(out_ulaw) == len(audio)
