"""
Unit tests for SatyaSwar Replay Attack Detection.
Authoritative source: Master Prompt Critical Requirement 1 & Implementation.md Section 7.
"""

import numpy as np

from satyaswar_ml.detection.replay import ReplayAttackDetector, ReplayResult


def test_replay_detector_initialization():
    detector = ReplayAttackDetector(sample_rate=16000)
    assert detector.sample_rate == 16000
    assert detector.replay_threshold == 0.65


def test_replay_detector_silence_or_short_speech():
    detector = ReplayAttackDetector(sample_rate=16000)
    # 3.5s of pure silence
    audio = np.zeros(56000, dtype=np.float32)
    mask = np.zeros(56000, dtype=bool)

    res = detector.analyze(audio, mask)
    assert isinstance(res, ReplayResult)
    assert res.is_conclusive is False
    assert res.replay_detected is False
    assert res.features.get("reason") == "audio_silent"



def test_replay_detector_simulated_live_speech():
    detector = ReplayAttackDetector(sample_rate=16000)
    t = np.linspace(0, 3.5, 56000, endpoint=False, dtype=np.float32)
    # Broad multi-harmonic rich spectrum simulating natural human phonation (no artificial rolloff)
    audio = (
        0.3 * np.sin(2 * np.pi * 180 * t)
        + 0.25 * np.sin(2 * np.pi * 360 * t)
        + 0.2 * np.sin(2 * np.pi * 720 * t)
        + 0.15 * np.sin(2 * np.pi * 1500 * t)
        + 0.1 * np.sin(2 * np.pi * 3200 * t)
        + 0.08 * np.sin(2 * np.pi * 5500 * t)  # Strong high-frequency presence (live microphone)
    )
    mask = np.ones(56000, dtype=bool)

    res = detector.analyze(audio, mask)
    assert res.is_conclusive is True
    # Live voice should have low replay probability
    assert res.replay_score < 0.60
    assert res.replay_detected is False


def test_replay_detector_simulated_loudspeaker_playback():
    detector = ReplayAttackDetector(sample_rate=16000)
    t = np.linspace(0, 3.5, 56000, endpoint=False, dtype=np.float32)
    # Loudspeaker playback:
    # 1. Heavy HF rolloff (>4kHz severely attenuated)
    # 2. Resonant midband peak (1.2 kHz - 2.5 kHz physical loudspeaker enclosure resonance)
    # 3. Flatter harmonic ratios
    audio = (
        0.1 * np.sin(2 * np.pi * 200 * t)
        + 0.6 * np.sin(2 * np.pi * 1800 * t)  # Heavy midband resonance
        + 0.5 * np.sin(2 * np.pi * 2200 * t)
        + 0.001 * np.sin(2 * np.pi * 5500 * t)  # Almost no HF
    )
    mask = np.ones(56000, dtype=bool)

    res = detector.analyze(audio, mask)
    assert res.is_conclusive is True
    # Loudspeaker artifacts should trigger elevated replay score
    assert res.replay_score >= 0.55
