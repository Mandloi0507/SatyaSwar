"""
Configuration loading and validation for SatyaSwar ML subsystem.
Authoritative source: Implementation.md, Section 4, 7, Appendix A.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class AudioConfig(BaseModel):
    sample_rate: int = 16000
    mode_default: Literal["chunks", "windows"] = "chunks"
    chunk_s: float = 1.75
    window_s: float = 3.5
    hop_s: float = 1.75
    ring_buffer_s: float = 8.0
    model_input_samples: int = 64600
    trim_silence_for_model: bool = True
    pad_mode: Literal["repeat", "zeros"] = "repeat"
    min_speech_s_for_scoring: float = 1.0
    max_frame_s: float = 10.0


class VadConfig(BaseModel):
    threshold: float = 0.5
    min_speech_ms: int = 250
    min_silence_ms: int = 100


class DetectorConfig(BaseModel):
    primary: str = "xlsr300m_aasist_ft"
    secondary: str | None = None
    device: Literal["auto", "cuda", "cpu"] = "auto"
    precision: Literal["fp16", "fp32"] = "fp16"
    checkpoint_path: str = "models/xlsr300m_aasist_ft.pth"
    max_pending_windows: int = 2


class EvidenceConfig(BaseModel):
    w_speech: float = 0.45
    w_snr: float = 0.30
    w_agreement: float = 0.25
    good_min: float = 0.70
    fair_min: float = 0.45


class ScoringConfig(BaseModel):
    alpha_base: float = 0.6
    escalate_consecutive: int = 2
    deescalate_consecutive: int = 3
    hysteresis_delta: float = 0.05
    immediate_high_margin: float = 0.15
    min_alert_spacing_s: float = 6.0
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)


class AsrConfig(BaseModel):
    enabled: bool = True
    model: str = "small"
    device: Literal["auto", "cuda", "cpu"] = "auto"
    compute_type: Literal["auto", "float16", "int8"] = "auto"
    trigger_speech_s: list[int] = Field(default_factory=lambda: [6, 12])
    max_speech_s: int = 12
    languages: list[str] = Field(default_factory=lambda: ["en", "hi"])
    language_confidence_min: float = 0.7
    beam_size: int = 1


class TelephonyConfig(BaseModel):
    default_profile: str = "none"
    profiles: list[str] = Field(
        default_factory=lambda: ["none", "g711_ulaw", "g711_alaw", "amr_nb", "gsm", "opus_8k"]
    )


class PrivacyConfig(BaseModel):
    debug_dump_audio: bool = False
    log_transcripts: bool = False


class SessionConfigSettings(BaseModel):
    resume_window_s: int = 60


class ThresholdPair(BaseModel):
    low_max: float = Field(..., ge=0.0, le=1.0)
    high_min: float = Field(..., ge=0.0, le=1.0)

    @field_validator("high_min")
    @classmethod
    def validate_bounds(cls, v: float, info: Any) -> float:
        low_max = info.data.get("low_max")
        if low_max is not None and v <= low_max:
            raise ValueError(f"high_min ({v}) must be strictly greater than low_max ({low_max})")
        return v


class ThresholdsConfig(BaseModel):
    default: ThresholdPair = Field(default_factory=lambda: ThresholdPair(low_max=0.35, high_min=0.65))
    hi: ThresholdPair = Field(default_factory=lambda: ThresholdPair(low_max=0.35, high_min=0.65))
    en: ThresholdPair = Field(default_factory=lambda: ThresholdPair(low_max=0.35, high_min=0.65))


class SatyaSwarConfig(BaseModel):
    schema_version: str = "1.0"
    env: Literal["dev", "demo"] = "dev"
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vad: VadConfig = Field(default_factory=VadConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    asr: AsrConfig = Field(default_factory=AsrConfig)
    telephony: TelephonyConfig = Field(default_factory=TelephonyConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    session: SessionConfigSettings = Field(default_factory=SessionConfigSettings)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)

    # Runtime overrides
    mock_mode: bool = False

    @field_validator("env")
    @classmethod
    def validate_demo_privacy(cls, v: str, info: Any) -> str:
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.env == "demo" and self.privacy.debug_dump_audio:
            raise ValueError("demo environment strictly forbids debug_dump_audio")



def _find_file(filename: str, base_dirs: list[Path] | None = None) -> Path:
    """Find a configuration file relative to CWD or package root."""
    if base_dirs is None:
        base_dirs = [
            Path.cwd(),
            Path.cwd() / "configs",
            Path(__file__).parent.parent.parent / "configs",
            Path(__file__).parent.parent.parent,
        ]
    for d in base_dirs:
        candidate = d / filename if not filename.startswith(str(d)) else Path(filename)
        if candidate.is_file():
            return candidate
    return Path(filename)


def load_config(
    config_path: str | Path | None = None,
    thresholds_path: str | Path | None = None,
) -> SatyaSwarConfig:
    """
    Load configuration from YAML and apply environment variable overrides.
    Authoritative rules:
    - Never write audio/transcripts if env == 'demo'.
    - Apply ML_* environment variable overrides.
    """
    # 1. Resolve path
    if not config_path:
        config_path = os.getenv("ML_CONFIG_PATH", "configs/default.yaml")
    cfg_file = _find_file(str(config_path))

    data: dict[str, Any] = {}
    if cfg_file.is_file():
        with open(cfg_file, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                data = loaded

    # 2. Resolve thresholds
    if not thresholds_path:
        thresholds_path = "configs/thresholds.yaml"
    thresh_file = _find_file(str(thresholds_path))
    if thresh_file.is_file():
        with open(thresh_file, "r", encoding="utf-8") as f:
            loaded_thresh = yaml.safe_load(f)
            if isinstance(loaded_thresh, dict):
                data["thresholds"] = loaded_thresh

    # 3. Apply Environment Variable Overrides
    if env_val := os.getenv("ML_ENV"):
        data["env"] = env_val

    if device_val := os.getenv("ML_DEVICE"):
        data.setdefault("detector", {})["device"] = device_val

    mock_env = os.getenv("ML_MOCK", "0") in ("1", "true", "True")

    # Privacy safety rule from Section 14
    if data.get("env") == "demo":
        data.setdefault("privacy", {})["debug_dump_audio"] = False
        data.setdefault("privacy", {})["log_transcripts"] = False

    # 4. Instantiate & Validate
    config = SatyaSwarConfig.model_validate(data)
    config.mock_mode = mock_env
    return config
