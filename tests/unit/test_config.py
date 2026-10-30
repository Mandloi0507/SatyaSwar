"""
Unit tests for SatyaSwar ML configuration loader.
Authoritative source: Implementation.md, Section 4, 7, Appendix A.
"""

import pytest
from pydantic import ValidationError

from satyaswar_ml.config import SatyaSwarConfig, ThresholdPair, load_config


class TestConfigLoader:
    def test_load_default_config(self):
        cfg = load_config()
        assert isinstance(cfg, SatyaSwarConfig)
        assert cfg.schema_version == "1.0"
        assert cfg.audio.sample_rate == 16000
        assert cfg.audio.chunk_s == 1.75
        assert cfg.audio.window_s == 3.5
        assert cfg.audio.hop_s == 1.75
        assert cfg.audio.model_input_samples == 64600
        assert cfg.detector.primary == "xlsr300m_aasist_ft"
        assert cfg.thresholds.default.low_max < cfg.thresholds.default.high_min

    def test_env_override_device(self, monkeypatch):
        monkeypatch.setenv("ML_DEVICE", "cpu")
        cfg = load_config()
        assert cfg.detector.device == "cpu"

    def test_env_override_mock(self, monkeypatch):
        monkeypatch.setenv("ML_MOCK", "1")
        cfg = load_config()
        assert cfg.mock_mode is True

    def test_demo_env_enforces_privacy(self, monkeypatch):
        """In demo environment, debug dumps MUST be strictly disabled."""
        monkeypatch.setenv("ML_ENV", "demo")
        cfg = load_config()
        assert cfg.env == "demo"
        assert cfg.privacy.debug_dump_audio is False
        assert cfg.privacy.log_transcripts is False

    def test_invalid_threshold_bounds_rejected(self):
        with pytest.raises(ValidationError):
            ThresholdPair(low_max=0.70, high_min=0.30)  # high_min <= low_max is invalid
