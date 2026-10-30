"""
SatyaSwar - Configuration Module
Member 2: Backend, Infrastructure, Database and Security

This module defines the central configuration management for the FastAPI backend using
Pydantic Settings. It loads environment variables from a .env file, provides sensible
development defaults, ignores unrecognized extra environment variables, and caches the
settings instance using lru_cache.

NOTE: Audio and risk engine configurations are provisional contracts and must be confirmed
with Member 1 (Flutter client) and Member 3 (ML/audio analysis).
"""

import json
from functools import lru_cache
from typing import Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and/or .env file.
    Sensible defaults are provided for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Application Configuration
    # --------------------------------------------------------------------------
    app_env: str = Field(
        default="development",
        description="Application runtime environment (e.g. 'development', 'production')",
    )
    firebase_project_id: str = Field(
        default="",
        description="Firebase project ID for Firebase Admin SDK",
    )
    google_application_credentials: str = Field(
        default="",
        description="Path to service account JSON key file for local development",
    )
    cors_origins: Union[list[str], str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins for the API",
    )

    # --------------------------------------------------------------------------
    # ML Integration Settings
    # --------------------------------------------------------------------------
    ml_service_url: str = Field(
        default="http://localhost:9000",
        description="Base URL for Member 3's ML audio analysis service",
    )
    ml_timeout_seconds: float = Field(
        default=3.0,
        gt=0.0,
        description="Timeout in seconds for ML inference HTTP requests",
    )

    # --------------------------------------------------------------------------
    # Audio Settings (PROVISIONAL - Subject to confirmation by Member 1 and Member 3)
    # --------------------------------------------------------------------------
    audio_sample_rate: int = Field(
        default=16000,
        gt=0,
        description="Audio sample rate in Hz (standard: 16000 Hz)",
    )
    audio_channels: int = Field(
        default=1,
        gt=0,
        description="Audio channels count (1 for mono PCM audio)",
    )
    audio_window_seconds: float = Field(
        default=3.5,
        gt=0.0,
        description="Duration of each audio analysis window in seconds (3.5 s = 56000 samples at 16 kHz)",
    )
    audio_hop_seconds: float = Field(
        default=1.75,
        gt=0.0,
        description="Hop interval between consecutive windows in seconds (1.75 s = 28000 samples at 16 kHz, 50% overlap)",
    )
    audio_sample_width_bytes: int = Field(
        default=2,
        gt=0,
        description="Bytes per sample (2 bytes for PCM signed 16-bit little-endian)",
    )

    # --------------------------------------------------------------------------
    # Risk Engine Settings (PROVISIONAL - Configurable thresholds, not validated decisions)
    # --------------------------------------------------------------------------
    risk_alpha: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Exponential moving average smoothing factor alpha for rolling risk aggregation",
    )
    risk_high_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Threshold at or above which risk is classified as HIGH",
    )
    risk_low_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Threshold at or below which risk is classified as LOW",
    )
    min_evidence_quality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum evidence quality score required before updating rolling risk",
    )

    # --------------------------------------------------------------------------
    # Verification Settings
    # --------------------------------------------------------------------------
    verification_ttl_seconds: int = Field(
        default=120,
        gt=0,
        description="Time-to-live in seconds for caller verification requests (default: 120 s)",
    )
    verification_max_attempts: int = Field(
        default=3,
        gt=0,
        description="Maximum attempts allowed to respond to/match a verification code",
    )
    verification_hmac_secret: str = Field(
        default="",
        description="HMAC secret used for cryptographic hashing and validation of verification codes",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        """Allow comma-separated strings or JSON-encoded lists from environment variables."""
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_thresholds(self) -> "Settings":
        """Ensure risk thresholds are logically consistent."""
        if self.risk_low_threshold > self.risk_high_threshold:
            raise ValueError(
                f"risk_low_threshold ({self.risk_low_threshold}) cannot exceed "
                f"risk_high_threshold ({self.risk_high_threshold})"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of the Settings object.
    Uses lru_cache to avoid reading the environment and .env file repeatedly.
    """
    return Settings()
