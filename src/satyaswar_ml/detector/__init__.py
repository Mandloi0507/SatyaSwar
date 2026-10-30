"""Detector package for SatyaSwar ML subsystem."""
from satyaswar_ml.detector.base import Detector, DetectorOutput
from satyaswar_ml.detector.deepfense_backend import DeepFenseDetector
from satyaswar_ml.detector.ensemble import EnsembleDetector
from satyaswar_ml.detector.hf_backend import HuggingFaceDetector
from satyaswar_ml.detector.mock_detector import MockDetector
from satyaswar_ml.detector.registry import get_detector, register_detector

__all__ = [
    "DeepFenseDetector",
    "Detector",
    "DetectorOutput",
    "EnsembleDetector",
    "HuggingFaceDetector",
    "MockDetector",
    "get_detector",
    "register_detector",
]
