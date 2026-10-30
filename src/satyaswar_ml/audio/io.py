"""
Audio I/O, PCM16 conversion, and resampling helpers.
Authoritative source: Implementation.md, Section 7.1

- Audio format: PCM16 Little-Endian, 16 kHz, Mono.
- Pure in-memory processing: zero disk writes.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio.functional as F

TARGET_SAMPLE_RATE = 16000


def pcm16le_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """
    Convert raw PCM16 little-endian bytes to normalized float32 numpy array in [-1.0, 1.0].
    Strictly validates byte length (rejects odd byte counts).
    """
    if len(pcm_bytes) % 2 != 0:
        raise ValueError(f"Invalid PCM16 byte count: {len(pcm_bytes)} bytes is not a multiple of 2")
    if len(pcm_bytes) == 0:
        return np.empty(0, dtype=np.float32)

    # Convert bytes to int16, then float32 scaled to [-1.0, 1.0]
    int16_arr = np.frombuffer(pcm_bytes, dtype="<i2")
    float32_arr = int16_arr.astype(np.float32) / 32768.0
    return float32_arr


def float32_to_pcm16le(audio: np.ndarray) -> bytes:
    """
    Convert float32 numpy array in [-1.0, 1.0] to raw PCM16 little-endian bytes.
    Clips values to avoid int16 overflow wrap-around.
    """
    if audio.size == 0:
        return b""
    clipped = np.clip(audio, -1.0, 1.0)
    int16_arr = (clipped * 32767.0).astype("<i2")
    return int16_arr.tobytes()


def resample_audio(
    audio: np.ndarray,
    orig_sr: int,
    target_sr: int = TARGET_SAMPLE_RATE,
) -> np.ndarray:
    """
    Resample 1D float32 audio numpy array from orig_sr to target_sr using torchaudio.
    """
    if orig_sr == target_sr:
        return audio.astype(np.float32)
    if audio.size == 0:
        return np.empty(0, dtype=np.float32)

    tensor = torch.from_numpy(audio.astype(np.float32)).unsqueeze(0)
    resampled_tensor = F.resample(tensor, orig_freq=orig_sr, new_freq=target_sr)
    return resampled_tensor.squeeze(0).numpy()


def load_audio_from_bytes(data: bytes) -> tuple[np.ndarray, int]:
    """
    Read audio file bytes (WAV, FLAC, etc.) in memory, convert to mono, and resample to 16 kHz.
    Returns (audio_float32, 16000).
    """
    bio = io.BytesIO(data)
    audio, sr = sf.read(bio, dtype="float32")
    if audio.ndim > 1:
        # Convert multi-channel to mono via channel average
        audio = np.mean(audio, axis=1)
    if sr != TARGET_SAMPLE_RATE:
        audio = resample_audio(audio, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)
    return audio, TARGET_SAMPLE_RATE


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """
    Load an audio file from disk for testing/evaluation, convert to mono float32, and resample to 16 kHz.
    """
    audio, sr = sf.read(str(path), dtype="float32")
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != TARGET_SAMPLE_RATE:
        audio = resample_audio(audio, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)
    return audio, TARGET_SAMPLE_RATE
