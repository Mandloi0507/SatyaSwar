"""
Unit tests for detector protocol, registry, mock detector, and ensemble.
Authoritative source: Implementation.md, Section 7.4, 15.1
"""

import numpy as np
import pytest

from satyaswar_ml.detector.base import Detector, DetectorOutput
from satyaswar_ml.detector.ensemble import EnsembleDetector
from satyaswar_ml.detector.mock_detector import MockDetector
from satyaswar_ml.detector.registry import get_detector


class TestDetectorRegistryAndMock:
    def test_mock_detector_implements_protocol(self):
        detector = MockDetector(default_spoof_prob=0.85)
        assert isinstance(detector, Detector)
        assert detector.input_samples == 64600

    def test_mock_detector_warmup_and_predict(self):
        detector = MockDetector(default_spoof_prob=0.75)
        detector.warmup()

        dummy_wav = np.zeros(64600, dtype=np.float32)
        out = detector.predict(dummy_wav)
        assert isinstance(out, DetectorOutput)
        assert 0.0 <= out.spoof_prob <= 1.0
        assert out.raw.get("mock") is True

    def test_mock_detector_scripted_scores(self):
        scripted = [0.10, 0.25, 0.85, 0.92]
        detector = MockDetector(scripted_scores=scripted)

        scores = [detector.predict(np.zeros(64600, dtype=np.float32)).spoof_prob for _ in range(4)]
        assert scores == scripted

    def test_registry_lookup(self):
        det = get_detector("mock_detector")
        assert isinstance(det, MockDetector)

    def test_unregistered_detector_raises_key_error(self):
        with pytest.raises(KeyError, match="Unregistered detector"):
            get_detector("nonexistent_detector_name")

    def test_ensemble_detector(self):
        d1 = MockDetector(scripted_scores=[0.80])
        d2 = MockDetector(scripted_scores=[0.90])
        ens = EnsembleDetector([d1, d2])

        ens.warmup()
        out = ens.predict(np.zeros(64600, dtype=np.float32))
        assert out.spoof_prob == pytest.approx(0.85, abs=1e-3)
        assert out.raw["model_agreement"] == pytest.approx(0.90, abs=1e-3)
