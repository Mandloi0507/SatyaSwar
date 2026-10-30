"""
SatyaSwar - ML Audio Analysis Service Adapter
Member 2: Backend, Infrastructure, Database and Security

Provides an asynchronous HTTP adapter communicating with Member 3's ML audio
analysis inference service. Strictly enforces timeouts, input/output validation,
and never logs raw audio payloads.
"""

import logging
import math
from typing import Any, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class MLUnavailable(Exception):
    """Raised when the ML inference service fails, times out, or returns invalid data."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_ml_output(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validates output payload from ML inference service.
    Ensures scores and quality metrics are finite numbers within [0.0, 1.0].
    Explicitly rejects NaN, Infinity, and -Infinity.
    """
    if not isinstance(data, dict):
        raise MLUnavailable("ML response is not a valid JSON object")

    for key in ("spoof_score", "evidence_quality"):
        val = data.get(key)
        if val is None or not isinstance(val, (int, float)):
            raise MLUnavailable(f"Invalid or missing value for '{key}': {val}")
        fval = float(val)
        if not math.isfinite(fval):
            raise MLUnavailable(f"Non-finite value for '{key}': {val}")
        if not (0.0 <= fval <= 1.0):
            raise MLUnavailable(f"Out-of-range value for '{key}': {val}")

    return data


class MLClient:
    """
    Async HTTP client adapter for Member 3's audio analysis inference service.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        settings = get_settings()
        self.base_url = base_url or settings.ml_service_url
        self.timeout = timeout if timeout is not None else settings.ml_timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=transport,
        )

    async def score_window(
        self,
        session_id: str,
        window_id: int,
        pcm_bytes: bytes,
    ) -> dict[str, Any]:
        """
        Submits a single PCM audio window to Member 3's ML service.

        Privacy notice: Raw audio bytes are transmitted over HTTP in-transit to the ML
        service, but NEVER logged or persisted to disk or database.

        Raises:
            MLUnavailable: On network timeout, connection error, non-200 HTTP status,
                           or malformed/uncalibrated score response.
        """
        settings = get_settings()
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Session-Id": session_id,
            "X-Window-Id": str(window_id),
            "X-Sample-Rate": str(settings.audio_sample_rate),
            "X-Sample-Width": str(settings.audio_sample_width_bytes),
            "X-Channels": str(settings.audio_channels),
        }

        try:
            response = await self._client.post(
                "/predict",
                content=pcm_bytes,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as e:
            logger.warning(
                "ML inference timeout for session %s, window %s after %.1fs",
                session_id,
                window_id,
                self.timeout,
            )
            raise MLUnavailable(f"ML service timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.warning(
                "ML service returned HTTP %s for session %s, window %s",
                e.response.status_code,
                session_id,
                window_id,
            )
            raise MLUnavailable(
                f"ML service error: HTTP {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("ML request failed for session %s, window %s: %s", session_id, window_id, e)
            raise MLUnavailable(f"ML service request failed: {e}") from e

        validated = validate_ml_output(data)
        return validated

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        await self._client.aclose()

