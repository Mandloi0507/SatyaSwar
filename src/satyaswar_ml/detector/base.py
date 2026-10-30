"""
Anti-spoofing detector protocol and output structures.
Authoritative source: Implementation.md, Section 7.4
"""

from __future__ import annotations

from typing import Any, NamedTuple, Protocol, runtime_checkable

import numpy as np


class DetectorOutput(NamedTuple):
    spoof_prob: float                # [0.0, 1.0], higher = more likely synthetic (Contract D3)
    raw: dict[str, Any]              # Logits or backend diagnostics (for telemetry/debugging)


@runtime_checkable
class Detector(Protocol):
    """Protocol satisfied by all anti-spoofing detector backends."""
    name: str
    version: str
    input_samples: int

    def warmup(self) -> None:
        """Run warm-up inference on a dummy tensor to prime CUDA/JIT cache."""
        ...

    def predict(self, wav: np.ndarray) -> DetectorOutput:
        """
        Run inference on 1D float32 audio array of length input_samples at 16 kHz.
        Must return DetectorOutput with spoof_prob in [0.0, 1.0].
        """
        ...
