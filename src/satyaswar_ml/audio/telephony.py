"""
Telephony simulation filters and degradation profiles.
Authoritative source: Implementation.md, Section 7.10

Simulates telephony narrowband codecs (8 kHz) on 16 kHz window audio:
- In-memory G.711 mu-law and A-law via Python 3.10 audioop.
- FFmpeg subprocess pipes for AMR-NB, GSM, and Opus with encoder capability detection.
"""

from __future__ import annotations

import audioop
import shutil
import subprocess

import numpy as np

from satyaswar_ml.audio.io import (
    float32_to_pcm16le,
    pcm16le_to_float32,
    resample_audio,
)

_AVAILABLE_FFMPEG_ENCODERS: set[str] | None = None


def get_available_ffmpeg_encoders() -> set[str]:
    """Inspect ffmpeg -encoders to determine available codec encoders."""
    global _AVAILABLE_FFMPEG_ENCODERS
    if _AVAILABLE_FFMPEG_ENCODERS is not None:
        return _AVAILABLE_FFMPEG_ENCODERS

    encoders: set[str] = set()
    if not shutil.which("ffmpeg"):
        _AVAILABLE_FFMPEG_ENCODERS = encoders
        return encoders

    try:
        proc = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].startswith("A"):
                encoders.add(parts[1].lower())
    except Exception:
        pass

    _AVAILABLE_FFMPEG_ENCODERS = encoders
    return encoders


def apply_g711_ulaw(audio: np.ndarray) -> np.ndarray:
    """
    Simulate G.711 mu-law narrowband telephony in memory:
    16 kHz mono -> downsample to 8 kHz -> mu-law compand (8-bit) -> expand to 16-bit -> upsample to 16 kHz.
    """
    if len(audio) == 0:
        return audio

    # 1. Downsample to 8 kHz
    audio_8k = resample_audio(audio, orig_sr=16000, target_sr=8000)

    # 2. Convert to PCM16 bytes
    pcm_8k = float32_to_pcm16le(audio_8k)

    # 3. audioop mu-law companding (16-bit to 8-bit mu-law, then back to 16-bit linear)
    ulaw_bytes = audioop.lin2ulaw(pcm_8k, 2)
    decompanded_pcm = audioop.ulaw2lin(ulaw_bytes, 2)

    # 4. Convert back to float32 and upsample to 16 kHz
    decompanded_audio = pcm16le_to_float32(decompanded_pcm)
    out = resample_audio(decompanded_audio, orig_sr=8000, target_sr=16000)

    # Match input length exactly
    if len(out) > len(audio):
        return out[:len(audio)]
    elif len(out) < len(audio):
        pad = np.zeros(len(audio) - len(out), dtype=np.float32)
        return np.concatenate([out, pad])
    return out


def apply_g711_alaw(audio: np.ndarray) -> np.ndarray:
    """
    Simulate G.711 A-law narrowband telephony in memory:
    16 kHz mono -> downsample to 8 kHz -> A-law compand (8-bit) -> expand to 16-bit -> upsample to 16 kHz.
    """
    if len(audio) == 0:
        return audio

    # 1. Downsample to 8 kHz
    audio_8k = resample_audio(audio, orig_sr=16000, target_sr=8000)

    # 2. Convert to PCM16 bytes
    pcm_8k = float32_to_pcm16le(audio_8k)

    # 3. audioop A-law companding
    alaw_bytes = audioop.lin2alaw(pcm_8k, 2)
    decompanded_pcm = audioop.alaw2lin(alaw_bytes, 2)

    # 4. Convert back to float32 and upsample to 16 kHz
    decompanded_audio = pcm16le_to_float32(decompanded_pcm)
    out = resample_audio(decompanded_audio, orig_sr=8000, target_sr=16000)

    if len(out) > len(audio):
        return out[:len(audio)]
    elif len(out) < len(audio):
        pad = np.zeros(len(audio) - len(out), dtype=np.float32)
        return np.concatenate([out, pad])
    return out


def _run_ffmpeg_codec_filter(audio: np.ndarray, ffmpeg_args: list[str]) -> np.ndarray:
    """Run FFmpeg piped audio through a codec encode/decode chain."""
    if len(audio) == 0:
        return audio

    pcm_in = float32_to_pcm16le(audio)
    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-f", "s16le",
        "-ar", "16000",
        "-ac", "1",
        "-i", "pipe:0",
        *ffmpeg_args,
        "-f", "s16le",
        "-ar", "16000",
        "-ac", "1",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=pcm_in,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if proc.returncode == 0 and len(proc.stdout) > 0:
            out = pcm16le_to_float32(proc.stdout)
            if len(out) > len(audio):
                return out[:len(audio)]
            elif len(out) < len(audio):
                pad = np.zeros(len(audio) - len(out), dtype=np.float32)
                return np.concatenate([out, pad])
            return out
    except Exception:
        pass

    # Fallback to G.711 mu-law if subprocess fails
    return apply_g711_ulaw(audio)


def apply_amr_nb(audio: np.ndarray) -> np.ndarray:
    """AMR-NB (8 kHz mobile narrowband) simulation via FFmpeg."""
    encoders = get_available_ffmpeg_encoders()
    if "libopencore_amrnb" in encoders:
        return _run_ffmpeg_codec_filter(
            audio,
            ["-c:a", "libopencore_amrnb", "-ar", "8000", "-b:a", "12.2k"],
        )
    return apply_g711_ulaw(audio)


def apply_gsm(audio: np.ndarray) -> np.ndarray:
    """GSM 06.10 Full Rate (8 kHz cellular audio) simulation via FFmpeg."""
    encoders = get_available_ffmpeg_encoders()
    if "libgsm" in encoders or "gsm" in encoders:
        codec = "libgsm" if "libgsm" in encoders else "gsm"
        return _run_ffmpeg_codec_filter(audio, ["-c:a", codec, "-ar", "8000"])
    return apply_g711_ulaw(audio)


def apply_opus_8k(audio: np.ndarray) -> np.ndarray:
    """Opus 8 kHz low-bitrate VoIP speech codec simulation via FFmpeg."""
    encoders = get_available_ffmpeg_encoders()
    if "libopus" in encoders:
        return _run_ffmpeg_codec_filter(
            audio,
            ["-c:a", "libopus", "-ar", "8000", "-b:a", "8k", "-application", "voip"],
        )
    return apply_g711_ulaw(audio)


def apply_telephony_profile(audio: np.ndarray, profile: str) -> np.ndarray:
    """
    Dispatcher applying the requested telephony degradation chain to a 16 kHz window.
    Profiles: 'none', 'g711_ulaw', 'g711_alaw', 'amr_nb', 'gsm', 'opus_8k'.
    """
    if profile == "none" or not profile:
        return audio
    if profile == "g711_ulaw":
        return apply_g711_ulaw(audio)
    if profile == "g711_alaw":
        return apply_g711_alaw(audio)
    if profile == "amr_nb":
        return apply_amr_nb(audio)
    if profile == "gsm":
        return apply_gsm(audio)
    if profile == "opus_8k":
        return apply_opus_8k(audio)
    return audio
