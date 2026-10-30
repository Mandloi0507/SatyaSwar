"""
Faster-Whisper ASR and Language Identification Wrapper.
Authoritative source: Implementation.md, Section 7.7

- Runs off the critical path in a dedicated background worker.
- Contact name biasing via initial_prompt.
- Language identification restricted to English ('en') and Hindi ('hi').
- Transcripts are dispatched transiently and dropped from memory immediately.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

import numpy as np
import torch

from satyaswar_ml.schemas import Contact


class AsrResult(NamedTuple):
    text: str
    language: str | None
    confidence: float | None
    is_final: bool
    start_ms: int
    end_ms: int


class WhisperASR:
    """
    Faster-Whisper ASR pipeline with language restriction and name biasing.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        language_confidence_min: float = 0.7,
    ):
        self.model_size = model_size
        self.language_confidence_min = language_confidence_min

        # Resolve device and compute_type
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if compute_type == "auto":
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        else:
            self.compute_type = compute_type

        self.model = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.is_available = True

    def load_model(self) -> None:
        """Load Faster-Whisper model into memory."""
        if self.model is not None:
            return

        with self._lock:
            if self.model is not None:
                return
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                self.is_available = True
            except Exception:
                self.is_available = False
                self.model = None

    def build_initial_prompt(self, contacts: list[Contact]) -> str:
        """
        Construct initial prompt containing contact display names and aliases
        in both Latin and Devanagari scripts to bias ASR decoding.
        """
        if not contacts:
            return ""

        names: list[str] = []
        for c in contacts:
            if c.display_name:
                names.append(c.display_name)
            for alias in c.aliases:
                if alias and alias not in names:
                    names.append(alias)

        if not names:
            return ""
        return "Names: " + ", ".join(names) + "."

    def transcribe(
        self,
        audio: np.ndarray,
        contacts: list[Contact] | None = None,
        is_final: bool = False,
        start_ms: int = 0,
        end_ms: int = 0,
    ) -> AsrResult | None:
        """
        Transcribe audio slice (float32 at 16 kHz) off the critical path.
        """
        if self.model is None:
            self.load_model()

        if self.model is None or not self.is_available:
            return None

        prompt = self.build_initial_prompt(contacts or [])

        try:
            # Language detection and transcription
            segments, info = self.model.transcribe(
                audio,
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,
                initial_prompt=prompt if prompt else None,
            )

            # Restrict language to 'en' or 'hi'
            detected_lang = None
            conf = float(info.language_probability) if hasattr(info, "language_probability") else 0.5
            if info.language in ("en", "hi") and conf >= self.language_confidence_min:
                detected_lang = info.language
            elif info.all_language_probs:
                # Check top between en and hi
                probs_dict = dict(info.all_language_probs)
                p_en = probs_dict.get("en", 0.0)
                p_hi = probs_dict.get("hi", 0.0)
                if p_hi >= p_en and p_hi >= 0.3:
                    detected_lang = "hi"
                    conf = p_hi
                elif p_en > p_hi and p_en >= 0.3:
                    detected_lang = "en"
                    conf = p_en

            text_parts = [seg.text for seg in segments]
            full_text = " ".join(text_parts).strip()

            return AsrResult(
                text=full_text,
                language=detected_lang,
                confidence=round(conf, 3),
                is_final=is_final,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        except Exception:
            return None
