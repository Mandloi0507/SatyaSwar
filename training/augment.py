"""
Data Augmentation for SatyaSwar Anti-Spoofing Model Training
Authoritative source: Implementation.md, Section 7.10, 9.4, 10.2

Applies telephony codec compression (G.711, GSM, AMR), additive background noise at SNR (20, 10, 5 dB),
and speed/pitch perturbations.
"""

from __future__ import annotations

import math

import numpy as np

from satyaswar_ml.audio.telephony import apply_telephony_profile


def add_gaussian_noise(audio: np.ndarray, snr_db: float) -> np.ndarray:
    """
    Add additive white Gaussian noise to audio at specified SNR (dB).
    """
    sig_power = float(np.mean(audio ** 2))
    if sig_power <= 1e-12:
        return audio

    noise_power = sig_power / (10.0 ** (snr_db / 10.0))
    noise = np.random.normal(0, math.sqrt(noise_power), size=audio.shape).astype(np.float32)
    return np.clip(audio + noise, -1.0, 1.0)


def apply_codec_augmentation(audio: np.ndarray, profile: str) -> np.ndarray:
    """
    Apply telephony channel degradation (g711_ulaw, g711_alaw, gsm, amr_nb).
    """
    return apply_telephony_profile(audio, profile=profile)


def random_speed_perturbation(audio: np.ndarray, speed_factor: float = 1.0) -> np.ndarray:
    """
    Simulate slight network streaming jitter and speed variations.
    Uses linear interpolation.
    """
    if abs(speed_factor - 1.0) < 1e-3:
        return audio

    n = len(audio)
    target_n = int(round(n / speed_factor))
    indices = np.linspace(0, n - 1, target_n)
    resampled = np.interp(indices, np.arange(n), audio).astype(np.float32)
    return resampled


def augment_audio_clip(
    audio: np.ndarray,
    codec_profile: str | None = None,
    snr_db: float | None = None,
    speed_factor: float | None = None,
) -> np.ndarray:
    """
    Full composite augmentation pipeline for robust model training.
    """
    out = np.copy(audio)
    if speed_factor is not None:
        out = random_speed_perturbation(out, speed_factor)
    if codec_profile and codec_profile != "none":
        out = apply_codec_augmentation(out, codec_profile)
    if snr_db is not None:
        out = add_gaussian_noise(out, snr_db)
    return out
