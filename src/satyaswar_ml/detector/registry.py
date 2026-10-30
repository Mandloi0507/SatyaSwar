"""
Detector backend registry for runtime candidate selection.
Authoritative source: Implementation.md, Section 7.4
"""

from __future__ import annotations

from satyaswar_ml.detector.base import Detector
from satyaswar_ml.detector.deepfense_backend import DeepFenseDetector
from satyaswar_ml.detector.hf_backend import HuggingFaceDetector
from satyaswar_ml.detector.mock_detector import MockDetector

_DETECTOR_REGISTRY: dict[str, type[Detector]] = {
    "xlsr300m_aasist_ft": DeepFenseDetector,
    "mock_detector": MockDetector,
    "hf_classifier": HuggingFaceDetector,
}


def register_detector(name: str, detector_cls: type[Detector]) -> None:
    """Register a new detector candidate class."""
    _DETECTOR_REGISTRY[name] = detector_cls


def get_detector(name: str, **kwargs) -> Detector:
    """
    Instantiate a detector backend by registry key.
    Raises KeyError if unregistered.
    """
    if name not in _DETECTOR_REGISTRY:
        raise KeyError(
            f"Unregistered detector backend: '{name}'. "
            f"Available backends: {list(_DETECTOR_REGISTRY.keys())}"
        )
    cls = _DETECTOR_REGISTRY[name]
    return cls(**kwargs)
