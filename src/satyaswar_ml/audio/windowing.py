"""
Audio Windowing, RingBuffer, and Model Input Preparation.
Authoritative source: Implementation.md, Section 7.2

- 3.5 s analysis window (56,000 samples at 16 kHz)
- 1.75 s hop (28,000 samples at 16 kHz)
- 8.0 s fixed-size RingBuffer
- Model input repeat-padding to 64,600 samples (~4.04 s)
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np


class AudioWindow(NamedTuple):
    index: int
    audio: np.ndarray      # float32 array of length window_samples (56,000)
    start_ms: int
    end_ms: int
    is_final: bool = False


class RingBuffer:
    """
    Fixed-capacity circular audio buffer for transient in-memory call streaming.
    Guarantees no memory growth across call lifetime.
    """

    def __init__(self, capacity_samples: int):
        self.capacity = capacity_samples
        self.buffer = np.zeros(capacity_samples, dtype=np.float32)
        self.write_pos = 0
        self.total_samples_written = 0

    def append(self, samples: np.ndarray) -> None:
        """Append float32 audio samples into the circular buffer."""
        n = len(samples)
        if n == 0:
            return
        if n >= self.capacity:
            # New samples exceed capacity; keep only the latest capacity samples
            self.buffer[:] = samples[-self.capacity:]
            self.write_pos = 0
            self.total_samples_written += n
            return

        end_pos = self.write_pos + n
        if end_pos <= self.capacity:
            self.buffer[self.write_pos:end_pos] = samples
        else:
            first_chunk = self.capacity - self.write_pos
            self.buffer[self.write_pos:] = samples[:first_chunk]
            second_chunk = n - first_chunk
            self.buffer[:second_chunk] = samples[first_chunk:]
        self.write_pos = (self.write_pos + n) % self.capacity
        self.total_samples_written += n

    def get_latest(self, n_samples: int) -> np.ndarray:
        """Extract the most recent n_samples in chronological order."""
        if n_samples <= 0:
            return np.empty(0, dtype=np.float32)
        available = min(n_samples, self.total_samples_written, self.capacity)
        out = np.zeros(n_samples, dtype=np.float32)
        if available == 0:
            return out

        # Position of oldest of the requested samples
        start_pos = (self.write_pos - available) % self.capacity
        if start_pos + available <= self.capacity:
            out[-available:] = self.buffer[start_pos:start_pos + available]
        else:
            first_chunk = self.capacity - start_pos
            out[-available:-available + first_chunk] = self.buffer[start_pos:]
            second_chunk = available - first_chunk
            out[-second_chunk:] = self.buffer[:second_chunk]
        return out

    def clear(self) -> None:
        """Zero out buffer and reset pointers."""
        self.buffer.fill(0)
        self.write_pos = 0
        self.total_samples_written = 0


class WindowEmitter:
    """
    Emits 3.5 s windows (56,000 samples) with 1.75 s hop (28,000 samples).
    Supports both 'chunks' mode and 'windows' mode.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        window_s: float = 3.5,
        hop_s: float = 1.75,
        ring_buffer_s: float = 8.0,
        mode: str = "chunks",
    ):
        self.sample_rate = sample_rate
        self.window_samples = int(window_s * sample_rate)       # 56,000
        self.hop_samples = int(hop_s * sample_rate)             # 28,000
        self.mode = mode

        self.ring_buffer = RingBuffer(int(ring_buffer_s * sample_rate))
        self.samples_since_last_window = 0
        self.total_samples_ingested = 0
        self.next_window_index = 0
        self.last_window_end_sample = 0

    def push(self, samples: np.ndarray) -> list[AudioWindow]:
        """
        Ingest new audio samples and emit any windows that are ready.
        """
        if len(samples) == 0:
            return []

        if self.mode == "windows":
            # Window mode: payload is expected to be a full 3.5s window
            audio = samples
            if len(audio) < self.window_samples:
                # Pad to window length
                pad = np.zeros(self.window_samples - len(audio), dtype=np.float32)
                audio = np.concatenate([audio, pad])
            elif len(audio) > self.window_samples:
                audio = audio[:self.window_samples]

            start_ms = int((self.total_samples_ingested / self.sample_rate) * 1000)
            end_ms = int(((self.total_samples_ingested + self.window_samples) / self.sample_rate) * 1000)
            self.total_samples_ingested += len(samples)

            win = AudioWindow(
                index=self.next_window_index,
                audio=audio,
                start_ms=start_ms,
                end_ms=end_ms,
                is_final=False,
            )
            self.next_window_index += 1
            return [win]

        # Chunk mode: accumulate in ring buffer
        self.ring_buffer.append(samples)
        self.samples_since_last_window += len(samples)
        self.total_samples_ingested += len(samples)

        windows: list[AudioWindow] = []
        # First window triggers when total_samples >= window_samples
        # Subsequent windows trigger whenever samples_since_last_window >= hop_samples
        while True:
            if self.total_samples_ingested < self.window_samples:
                break

            if self.next_window_index == 0:
                # First window requires 3.5 s (56,000 samples)
                window_audio = self.ring_buffer.get_latest(self.window_samples)
                start_ms = 0
                end_ms = int((self.window_samples / self.sample_rate) * 1000)
                windows.append(
                    AudioWindow(
                        index=self.next_window_index,
                        audio=window_audio,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        is_final=False,
                    )
                )
                self.next_window_index += 1
                self.samples_since_last_window = self.total_samples_ingested - self.window_samples
                self.last_window_end_sample = self.window_samples

            elif self.samples_since_last_window >= self.hop_samples:
                # Subsequent window emitted after each hop
                window_audio = self.ring_buffer.get_latest(self.window_samples)
                end_sample = self.last_window_end_sample + self.hop_samples
                start_sample = end_sample - self.window_samples
                start_ms = int((start_sample / self.sample_rate) * 1000)
                end_ms = int((end_sample / self.sample_rate) * 1000)

                windows.append(
                    AudioWindow(
                        index=self.next_window_index,
                        audio=window_audio,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        is_final=False,
                    )
                )
                self.next_window_index += 1
                self.samples_since_last_window -= self.hop_samples
                self.last_window_end_sample = end_sample
            else:
                break

        return windows

    def flush(self, min_unscored_s: float = 1.5) -> AudioWindow | None:
        """
        End of call flush: if at least min_unscored_s of unscored audio remains,
        emit one final padded window.
        """
        min_samples = int(min_unscored_s * self.sample_rate)
        if self.samples_since_last_window < min_samples:
            return None

        # Build final window from latest available audio and repeat-pad
        latest_available = min(self.total_samples_ingested, self.window_samples)
        raw_audio = self.ring_buffer.get_latest(latest_available)
        final_audio = prepare_model_input(
            raw_audio,
            target_samples=self.window_samples,
            pad_mode="repeat",
        )

        end_sample = self.total_samples_ingested
        start_sample = max(0, end_sample - self.window_samples)
        start_ms = int((start_sample / self.sample_rate) * 1000)
        end_ms = int((end_sample / self.sample_rate) * 1000)

        win = AudioWindow(
            index=self.next_window_index,
            audio=final_audio,
            start_ms=start_ms,
            end_ms=end_ms,
            is_final=True,
        )
        self.next_window_index += 1
        self.samples_since_last_window = 0
        return win


def prepare_model_input(
    window_audio: np.ndarray,
    target_samples: int = 64600,
    trim_silence: bool = False,
    speech_segments: list[dict] | None = None,
    pad_mode: str = "repeat",
) -> np.ndarray:
    """
    Format audio for model inference:
    1. Optionally concatenate speech segments if trim_silence is True.
    2. Pad to target_samples (64,600 samples, ~4.04 s) via repeat-padding or zero-padding.
    """
    audio = window_audio.astype(np.float32)

    # 1. Silence trimming if requested
    if trim_silence and speech_segments and len(speech_segments) > 0:
        speech_parts = []
        for seg in speech_segments:
            start_idx = seg.get("start", 0)
            end_idx = seg.get("end", len(audio))
            if start_idx < len(audio) and end_idx > start_idx:
                speech_parts.append(audio[start_idx:min(end_idx, len(audio))])
        if speech_parts:
            concatenated = np.concatenate(speech_parts)
            # Only keep trimmed version if at least 0.5 s of speech remains
            if len(concatenated) >= 8000:
                audio = concatenated

    # 2. Pad or truncate to target_samples
    curr_len = len(audio)
    if curr_len == target_samples:
        return audio
    if curr_len > target_samples:
        return audio[:target_samples]

    if curr_len == 0:
        return np.zeros(target_samples, dtype=np.float32)

    if pad_mode == "repeat":
        # Repeat-padding (tile and slice)
        repeats = int(np.ceil(target_samples / curr_len))
        tiled = np.tile(audio, repeats)
        return tiled[:target_samples].astype(np.float32)
    else:
        # Zero-padding
        pad = np.zeros(target_samples - curr_len, dtype=np.float32)
        return np.concatenate([audio, pad]).astype(np.float32)
