"""
Silero VAD wrapper for active speech detection.
Authoritative source: Implementation.md, Section 7.3

- Runs on CPU over 16 kHz window audio.
- Detects speech segments, speech_seconds, and speech masks.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
import torch
from silero_vad import get_speech_timestamps, load_silero_vad


class VadResult(NamedTuple):
    speech_segments: list[dict[str, int]]   # List of {'start': int, 'end': int} in samples
    speech_seconds: float                   # Total speech duration in seconds
    speech_mask: np.ndarray                 # Boolean mask per audio sample (len == len(audio))
    frame_mask_10ms: np.ndarray             # Boolean mask per 10ms frame (160 samples)


class SileroVAD:
    """CPU-based voice activity detector using Silero VAD TorchScript JIT."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 100,
        sample_rate: int = 16000,
    ):
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.sample_rate = sample_rate

        # Load TorchScript model once on CPU
        self.model = load_silero_vad()
        self.model.eval()

    def detect(self, audio: np.ndarray) -> VadResult:
        """
        Run VAD on 1D float32 audio at 16 kHz.
        Returns VadResult with speech segments, speech_seconds, and masks.
        """
        n_samples = len(audio)
        if n_samples == 0:
            return VadResult(
                speech_segments=[],
                speech_seconds=0.0,
                speech_mask=np.zeros(0, dtype=bool),
                frame_mask_10ms=np.zeros(0, dtype=bool),
            )

        tensor_audio = torch.from_numpy(audio.astype(np.float32))
        with torch.no_grad():
            timestamps = get_speech_timestamps(
                tensor_audio,
                self.model,
                threshold=self.threshold,
                sampling_rate=self.sample_rate,
                min_speech_duration_ms=self.min_speech_ms,
                min_silence_duration_ms=self.min_silence_ms,
            )

        speech_mask = np.zeros(n_samples, dtype=bool)
        total_speech_samples = 0
        cleaned_segments: list[dict[str, int]] = []

        for seg in timestamps:
            st = max(0, seg["start"])
            en = min(n_samples, seg["end"])
            if en > st:
                speech_mask[st:en] = True
                total_speech_samples += (en - st)
                cleaned_segments.append({"start": st, "end": en})

        speech_seconds = float(total_speech_samples / self.sample_rate)

        # 10ms frame mask (160 samples per frame at 16 kHz)
        frame_len = int(0.010 * self.sample_rate)
        n_frames = n_samples // frame_len
        if n_frames > 0:
            # Reshape up to n_frames * frame_len and compute frame majority
            truncated_mask = speech_mask[:n_frames * frame_len].reshape(n_frames, frame_len)
            frame_mask_10ms = np.mean(truncated_mask, axis=1) >= 0.5
        else:
            frame_mask_10ms = np.zeros(0, dtype=bool)

        return VadResult(
            speech_segments=cleaned_segments,
            speech_seconds=round(speech_seconds, 3),
            speech_mask=speech_mask,
            frame_mask_10ms=frame_mask_10ms,
        )
