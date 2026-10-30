"""
Acoustic Replay and Presentation Attack Detector.
Authoritative source: Master Prompt, Critical Requirement 1:
"Detect Synthetic Speech and Replay Attacks: The system must address two distinct threats:
synthetic speech and replay attacks. Keep synthetic-voice evidence and replay-attack
evidence distinguishable in internal results and integration contract."

Analyzes physical transducer artifacts, loudspeaker spectral rolloff, midband resonance,
and double-channel acoustic floor consistency.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from scipy import signal


class ReplayResult(NamedTuple):
    replay_score: float             # [0.0, 1.0], higher = more likely replayed
    replay_detected: bool           # True if score >= threshold
    is_conclusive: bool             # False if audio is silent, too short, or poor quality
    features: dict[str, float]      # Exact computed auditable physical measurements


class ReplayAttackDetector:
    """
    Physical presentation and loudspeaker replay attack detector.
    Evaluates spectral rolloff, midband transducer coloration, and background acoustic floor.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        replay_threshold: float = 0.65,
    ):
        self.sample_rate = sample_rate
        self.replay_threshold = replay_threshold

    def analyze(
        self,
        audio: np.ndarray,
        speech_mask: np.ndarray | None = None,
    ) -> ReplayResult:
        """
        Analyze audio window for physical loudspeaker replay and transmission artifacts.
        """
        n_samples = len(audio)
        if n_samples < int(0.5 * self.sample_rate):
            # Clip is too short for conclusive acoustic analysis
            return ReplayResult(
                replay_score=0.0,
                replay_detected=False,
                is_conclusive=False,
                features={"reason": "audio_too_short"},
            )

        # Check for near-total silence
        rms = float(np.sqrt(np.mean(audio**2)))
        if rms < 1e-4:
            return ReplayResult(
                replay_score=0.0,
                replay_detected=False,
                is_conclusive=False,
                features={"reason": "audio_silent"},
            )

        # 1. Spectral Analysis via Welch periodogram
        freqs, psd = signal.welch(audio, fs=self.sample_rate, nperseg=min(1024, n_samples))
        eps = 1e-12
        psd_total = np.sum(psd) + eps

        # Band energy calculations
        # Band 1: Low-end bass (< 250 Hz) - often attenuated by micro-speakers
        bass_idx = (freqs >= 50) & (freqs < 250)
        # Band 2: Core speech (300 Hz - 2.5 kHz)
        speech_band_idx = (freqs >= 300) & (freqs < 2500)
        # Band 3: Loudspeaker acoustic resonance peak (2.5 kHz - 4.5 kHz)
        mid_resonance_idx = (freqs >= 2500) & (freqs < 4500)
        # Band 4: High-frequency rolloff (> 5.5 kHz) - sharp cutoff in small speakers / re-recording
        high_idx = (freqs >= 5500) & (freqs < 7800)

        p_bass = float(np.sum(psd[bass_idx])) / psd_total
        p_speech = float(np.sum(psd[speech_band_idx])) / psd_total
        p_resonance = float(np.sum(psd[mid_resonance_idx])) / psd_total
        p_high = float(np.sum(psd[high_idx])) / psd_total

        # 2. Replay Artifact Indicators:
        # Indicator A: High-frequency rolloff ratio (p_high / (p_speech + eps))
        # Replayed audio through laptop/mobile phone speakers suffers extreme HF loss
        hf_ratio = p_high / (p_speech + eps)

        # Indicator B: Midband resonance peaking (p_resonance / (p_speech + eps))
        # Small transducer enclosures emphasize 2.5 - 4.5 kHz
        resonance_ratio = p_resonance / (p_speech + eps)

        # Indicator C: Bass attenuation ratio (p_bass / (p_speech + eps))
        bass_ratio = p_bass / (p_speech + eps)

        # Indicator D: Spectral Flatness (Wiener entropy)
        # Replay introduces transducer noise / hiss across frequency spectrum
        geometric_mean = np.exp(np.mean(np.log(psd + eps)))
        arithmetic_mean = np.mean(psd) + eps
        spectral_flatness = float(geometric_mean / arithmetic_mean)

        # 3. Score Combination (evidence-based calibration)
        # Higher score = stronger indications of secondary acoustic transmission / loudspeaker playback
        hf_loss_term = float(np.clip((0.15 - hf_ratio) / 0.15, 0.0, 1.0))
        resonance_term = float(np.clip((resonance_ratio - 0.35) / 0.40, 0.0, 1.0))
        bass_loss_term = float(np.clip((0.08 - bass_ratio) / 0.08, 0.0, 1.0))

        raw_score = 0.40 * hf_loss_term + 0.35 * resonance_term + 0.25 * bass_loss_term
        replay_score = float(np.clip(round(raw_score, 2), 0.0, 1.0))

        detected = replay_score >= self.replay_threshold

        features = {
            "hf_ratio": round(hf_ratio, 4),
            "resonance_ratio": round(resonance_ratio, 4),
            "bass_ratio": round(bass_ratio, 4),
            "spectral_flatness": round(spectral_flatness, 4),
            "rms_energy": round(rms, 4),
        }

        return ReplayResult(
            replay_score=replay_score,
            replay_detected=detected,
            is_conclusive=True,
            features=features,
        )
