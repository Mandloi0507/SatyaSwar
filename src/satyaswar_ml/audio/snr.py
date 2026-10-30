"""
Signal-to-Noise Ratio (SNR) estimation from VAD mask.
Authoritative source: Implementation.md, Section 7.3

Computes mean power over active speech frames divided by mean power over non-speech frames in dB.
Uses the 10th percentile energy as the noise floor when non-speech frames are absent.
"""

from __future__ import annotations

import numpy as np


def compute_snr_db(
    audio: np.ndarray,
    speech_mask: np.ndarray,
    frame_size_samples: int = 160,
) -> float:
    """
    Estimate SNR in dB from 16 kHz audio and boolean speech mask.
    Returns estimated SNR in dB, bounded in [-10.0, 50.0].
    """
    if len(audio) == 0:
        return 0.0

    n_samples = len(audio)
    n_frames = n_samples // frame_size_samples
    if n_frames == 0:
        return 0.0

    # Reshape frames and compute root-mean-square or mean power per frame
    frames = audio[:n_frames * frame_size_samples].reshape(n_frames, frame_size_samples)
    frame_energies = np.mean(frames**2, axis=1)

    # Frame mask
    if len(speech_mask) >= n_frames * frame_size_samples:
        mask_frames = speech_mask[:n_frames * frame_size_samples].reshape(n_frames, frame_size_samples)
        frame_mask = np.mean(mask_frames, axis=1) >= 0.5
    else:
        frame_mask = np.zeros(n_frames, dtype=bool)

    speech_energies = frame_energies[frame_mask]
    noise_energies = frame_energies[~frame_mask]

    # Handle cases
    eps = 1e-9

    if len(speech_energies) == 0:
        # Zero speech detected; SNR is negative or 0
        return -5.0

    speech_power = float(np.mean(speech_energies))

    if len(noise_energies) > 0 and np.mean(noise_energies) > eps:
        noise_power = float(np.mean(noise_energies))
    else:
        # No non-speech frames present in this window; use 10th percentile of frame energy as noise floor
        noise_power = float(np.percentile(frame_energies, 10))
        noise_power = max(noise_power, eps)

    speech_power = max(speech_power, eps)
    snr = 10.0 * np.log10(speech_power / noise_power)
    return float(np.clip(round(snr, 1), -10.0, 50.0))
