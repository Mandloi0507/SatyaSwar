"""
Mock detector backend for offline, deterministic testing and mock mode.
Authoritative source: Implementation.md, Section 6.7, 7.4
"""

from __future__ import annotations

import numpy as np

from satyaswar_ml.detector.base import Detector, DetectorOutput


class MockDetector(Detector):
    """
    Deterministic detector returning scripted or parameterized spoof probabilities.
    Requires no GPU, no network access, and zero model weights.
    """

    def __init__(
        self,
        default_spoof_prob: float = 0.15,
        scripted_scores: list[float] | None = None,
        input_samples: int = 64600,
        version: str = "mock-1.0",
    ):
        self.name = "mock_detector"
        self.version = version
        self.input_samples = input_samples
        self.default_spoof_prob = default_spoof_prob
        self.scripted_scores = list(scripted_scores) if scripted_scores else []
        self._call_count = 0
        self._warmed_up = False

    def warmup(self) -> None:
        self._warmed_up = True

    def predict(self, wav: np.ndarray) -> DetectorOutput:
        self._call_count += 1
        rms = float(np.sqrt(np.mean(wav**2))) if len(wav) > 0 else 0.0

        if self.scripted_scores:
            idx = min(self._call_count - 1, len(self.scripted_scores) - 1)
            prob = self.scripted_scores[idx]
        else:
            prob = float(np.clip(self.default_spoof_prob + 0.05 * np.sin(self._call_count), 0.01, 0.99))

        return DetectorOutput(
            spoof_prob=round(prob, 3),
            raw={"mock": True, "call_index": self._call_count, "energy_rms": round(rms, 4)},
        )
