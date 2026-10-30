"""
Optional multi-model ensemble detector.
Authoritative source: Implementation.md, Section 7.4
"""

from __future__ import annotations

import numpy as np

from satyaswar_ml.detector.base import Detector, DetectorOutput


class EnsembleDetector(Detector):
    """
    Runs two detectors in parallel, averaging their spoof scores
    and computing inter-model agreement = 1 - |s1 - s2|.
    """

    def __init__(self, detectors: list[Detector], version: str = "ensemble-1.0"):
        if len(detectors) < 2:
            raise ValueError("EnsembleDetector requires at least two detectors")
        self.detectors = detectors
        self.name = "ensemble_" + "_".join(d.name for d in detectors)
        self.version = version
        self.input_samples = detectors[0].input_samples

    def warmup(self) -> None:
        for d in self.detectors:
            d.warmup()

    def predict(self, wav: np.ndarray) -> DetectorOutput:
        outputs = [d.predict(wav) for d in self.detectors]
        scores = [o.spoof_prob for o in outputs]
        mean_score = float(np.mean(scores))
        agreement = float(1.0 - np.abs(scores[0] - scores[1])) if len(scores) >= 2 else 1.0

        return DetectorOutput(
            spoof_prob=round(mean_score, 4),
            raw={
                "ensemble_scores": scores,
                "model_agreement": round(agreement, 4),
            },
        )
