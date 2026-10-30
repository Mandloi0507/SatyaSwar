"""
Unit tests for VAD, SNR estimation, evidence quality, and replay attack detection.
Authoritative source: Implementation.md, Section 7.3, 7.6 & Critical Requirement 1.
"""

from pathlib import Path

import numpy as np
import pytest
from scipy import signal

from satyaswar_ml.audio.snr import compute_snr_db
from satyaswar_ml.detection.replay import ReplayAttackDetector
from satyaswar_ml.scoring.evidence import compute_evidence_quality
from satyaswar_ml.vad.silero_vad import SileroVAD

FIXTURE_WAV = Path(__file__).parent.parent.parent / "vad_test.wav"


class TestSileroVAD:
    @pytest.fixture(scope="module")
    def vad_model(self):
        return SileroVAD(threshold=0.5, min_speech_ms=250, min_silence_ms=100)

    def test_synthetic_silence_yields_zero_speech(self, vad_model):
        silence = np.zeros(56000, dtype=np.float32)
        res = vad_model.detect(silence)
        assert res.speech_seconds == 0.0
        assert len(res.speech_segments) == 0
        assert np.all(~res.speech_mask)

    def test_white_noise_yields_zero_speech(self, vad_model):
        noise = np.random.normal(0, 0.05, 56000).astype(np.float32)
        res = vad_model.detect(noise)
        assert res.speech_seconds == 0.0
        assert len(res.speech_segments) == 0

    def test_real_speech_fixture_detects_speech(self, vad_model):
        if not FIXTURE_WAV.is_file():
            pytest.skip("vad_test.wav fixture not available")

        from satyaswar_ml.audio.io import load_audio
        wav, sr = load_audio(FIXTURE_WAV)
        assert sr == 16000

        # Run on the 16 kHz speech audio
        res = vad_model.detect(wav)
        assert res.speech_seconds > 1.0
        assert len(res.speech_segments) >= 1


class TestSNREstimation:
    def test_high_snr_speech_with_quiet_pauses(self):
        # 2 seconds speech, 1.5 seconds quiet
        audio = np.zeros(56000, dtype=np.float32)
        mask = np.zeros(56000, dtype=bool)

        # Speech burst at 0.5 amplitude
        audio[:32000] = 0.5 * np.sin(2 * np.pi * 300 * np.linspace(0, 2, 32000, dtype=np.float32))
        mask[:32000] = True

        # Background noise at 0.005 amplitude
        audio[32000:] = 0.005 * np.random.normal(0, 1, 24000).astype(np.float32)

        snr = compute_snr_db(audio, mask)
        assert snr > 20.0

    def test_all_speech_frames_uses_percentile_floor(self):
        audio = np.sin(2 * np.pi * 400 * np.linspace(0, 3.5, 56000, dtype=np.float32))
        mask = np.ones(56000, dtype=bool)

        snr = compute_snr_db(audio, mask)
        assert -10.0 <= snr <= 50.0

    def test_zero_speech_yields_negative_snr(self):
        audio = np.random.normal(0, 0.02, 56000).astype(np.float32)
        mask = np.zeros(56000, dtype=bool)

        snr = compute_snr_db(audio, mask)
        assert snr <= 0.0


class TestEvidenceQuality:
    def test_hard_gate_under_one_second_speech(self):
        ev = compute_evidence_quality(
            speech_seconds=0.7,
            snr_db=25.0,
            recent_scores=[0.8, 0.82],
            min_speech_s=1.0,
        )
        assert ev.is_sufficient is False
        assert ev.quality_label == "poor"
        assert ev.quality <= 0.35

    def test_high_quality_speech_window(self):
        ev = compute_evidence_quality(
            speech_seconds=3.2,
            snr_db=22.0,
            recent_scores=[0.1, 0.12, 0.11],
            min_speech_s=1.0,
        )
        assert ev.is_sufficient is True
        assert ev.quality_label == "good"
        assert ev.quality >= 0.70

    def test_fair_quality_window(self):
        ev = compute_evidence_quality(
            speech_seconds=1.5,
            snr_db=12.0,
            recent_scores=[0.3, 0.45],
            min_speech_s=1.0,
        )
        assert ev.is_sufficient is True
        assert ev.quality_label in ("fair", "poor")


class TestReplayAttackDetector:
    def test_silence_returns_inconclusive(self):
        detector = ReplayAttackDetector()
        silence = np.zeros(56000, dtype=np.float32)
        res = detector.analyze(silence)
        assert res.is_conclusive is False
        assert res.replay_detected is False

    def test_loudspeaker_replayed_audio_simulation(self):
        """
        Simulate acoustic loudspeaker transmission:
        - Heavy attenuation below 200 Hz
        - Resonant peaking in 2.5 - 4.5 kHz range
        - Sharp rolloff / cut-off above 5 kHz
        """
        detector = ReplayAttackDetector()
        t = np.linspace(0, 3.5, 56000, endpoint=False, dtype=np.float32)

        # Base wideband signal
        raw = np.sin(2 * np.pi * 500 * t) + 0.3 * np.random.normal(0, 0.1, 56000).astype(np.float32)

        # Apply bandpass simulating consumer phone speaker (cutoff < 250 Hz, resonant at 3.5 kHz, cutoff > 5 kHz)
        sos = signal.butter(4, [300, 4800], btype="bandpass", fs=16000, output="sos")
        replayed_sim = signal.sosfilt(sos, raw).astype(np.float32)

        # Add resonant midband peak
        replayed_sim += 0.8 * np.sin(2 * np.pi * 3200 * t).astype(np.float32)

        res = detector.analyze(replayed_sim)
        assert res.is_conclusive is True
        assert res.replay_score > 0.50
        assert "hf_ratio" in res.features
        assert "resonance_ratio" in res.features
