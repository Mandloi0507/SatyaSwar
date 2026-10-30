"""
SatyaSwar - ML Service Adapter Unit Tests
Tests the MLClient adapter using httpx.MockTransport, covering:
- Successful prediction with valid scores
- Timeout handling
- Non-200 HTTP responses
- Malformed JSON responses
- Invalid/out-of-range scores
- NaN and Infinity rejection
- Raw audio never in logs
- Configurable endpoint
- Request headers validation (X-Session-Id, X-Window-Id, X-Sample-Rate, X-Sample-Width, X-Channels)
"""

import json
import logging
import math
from unittest.mock import patch

import httpx
import pytest

from app.services.ml_service import MLClient, MLUnavailable, validate_ml_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PCM = b"\x00\x80" * 56000  # 112,000 bytes of silent 16-bit PCM


def _make_transport(handler):
    """Wraps a sync handler into an httpx.MockTransport."""
    return httpx.MockTransport(handler)


def _ok_response(spoof=0.75, quality=0.85, extra=None):
    """Returns a 200 JSON response with the given scores."""
    body = {"spoof_score": spoof, "evidence_quality": quality}
    if extra:
        body.update(extra)
    return httpx.Response(200, json=body)


# ---------------------------------------------------------------------------
# validate_ml_output unit tests
# ---------------------------------------------------------------------------

class TestValidateMLOutput:

    def test_valid_scores(self):
        data = {"spoof_score": 0.5, "evidence_quality": 0.9}
        result = validate_ml_output(data)
        assert result["spoof_score"] == 0.5
        assert result["evidence_quality"] == 0.9

    def test_boundary_zero(self):
        data = {"spoof_score": 0.0, "evidence_quality": 0.0}
        result = validate_ml_output(data)
        assert result["spoof_score"] == 0.0

    def test_boundary_one(self):
        data = {"spoof_score": 1.0, "evidence_quality": 1.0}
        result = validate_ml_output(data)
        assert result["spoof_score"] == 1.0

    def test_integer_scores_accepted(self):
        """int values (0 or 1) should be accepted as they are valid (int, float)."""
        data = {"spoof_score": 0, "evidence_quality": 1}
        result = validate_ml_output(data)
        assert result["spoof_score"] == 0

    def test_nan_rejected(self):
        data = {"spoof_score": float("nan"), "evidence_quality": 0.5}
        with pytest.raises(MLUnavailable, match="Non-finite"):
            validate_ml_output(data)

    def test_positive_infinity_rejected(self):
        data = {"spoof_score": 0.5, "evidence_quality": float("inf")}
        with pytest.raises(MLUnavailable, match="Non-finite"):
            validate_ml_output(data)

    def test_negative_infinity_rejected(self):
        data = {"spoof_score": float("-inf"), "evidence_quality": 0.5}
        with pytest.raises(MLUnavailable, match="Non-finite"):
            validate_ml_output(data)

    def test_out_of_range_high(self):
        data = {"spoof_score": 1.01, "evidence_quality": 0.5}
        with pytest.raises(MLUnavailable, match="Out-of-range"):
            validate_ml_output(data)

    def test_out_of_range_negative(self):
        data = {"spoof_score": 0.5, "evidence_quality": -0.1}
        with pytest.raises(MLUnavailable, match="Out-of-range"):
            validate_ml_output(data)

    def test_missing_key(self):
        data = {"spoof_score": 0.5}
        with pytest.raises(MLUnavailable, match="Invalid or missing"):
            validate_ml_output(data)

    def test_none_value(self):
        data = {"spoof_score": None, "evidence_quality": 0.5}
        with pytest.raises(MLUnavailable, match="Invalid or missing"):
            validate_ml_output(data)

    def test_string_value(self):
        data = {"spoof_score": "high", "evidence_quality": 0.5}
        with pytest.raises(MLUnavailable, match="Invalid or missing"):
            validate_ml_output(data)

    def test_not_a_dict(self):
        with pytest.raises(MLUnavailable, match="not a valid JSON object"):
            validate_ml_output([1, 2, 3])

    def test_extra_fields_preserved(self):
        data = {"spoof_score": 0.5, "evidence_quality": 0.9, "speech_duration": 3.5}
        result = validate_ml_output(data)
        assert result["speech_duration"] == 3.5


# ---------------------------------------------------------------------------
# MLClient adapter tests using MockTransport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMLClientAdapter:

    async def test_successful_prediction(self):
        """Valid prediction returns validated scores."""
        def handler(request):
            return _ok_response(0.88, 0.92)

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            result = await client.score_window("sess_1", 0, SAMPLE_PCM)
            assert result["spoof_score"] == 0.88
            assert result["evidence_quality"] == 0.92
        finally:
            await client.close()

    async def test_request_headers(self):
        """Verify all expected headers are sent to the ML service."""
        captured_headers = {}

        def handler(request):
            captured_headers.update(dict(request.headers))
            return _ok_response()

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            await client.score_window("sess_hdr", 3, SAMPLE_PCM)
        finally:
            await client.close()

        assert captured_headers.get("x-session-id") == "sess_hdr"
        assert captured_headers.get("x-window-id") == "3"
        assert captured_headers.get("x-sample-rate") == "16000"
        assert captured_headers.get("x-sample-width") == "2"
        assert captured_headers.get("x-channels") == "1"
        assert captured_headers.get("content-type") == "application/octet-stream"

    async def test_timeout_raises_ml_unavailable(self):
        """Network timeout must raise MLUnavailable."""
        def handler(request):
            raise httpx.ReadTimeout("read timed out")

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=0.01, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="timed out"):
                await client.score_window("sess_to", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_non_200_response(self):
        """Non-200 HTTP status must raise MLUnavailable with status code."""
        def handler(request):
            return httpx.Response(500, json={"error": "model crashed"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="HTTP 500") as exc_info:
                await client.score_window("sess_500", 0, SAMPLE_PCM)
            assert exc_info.value.status_code == 500
        finally:
            await client.close()

    async def test_non_200_403(self):
        """403 response must raise MLUnavailable with correct status code."""
        def handler(request):
            return httpx.Response(403, json={"error": "forbidden"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="HTTP 403") as exc_info:
                await client.score_window("sess_403", 0, SAMPLE_PCM)
            assert exc_info.value.status_code == 403
        finally:
            await client.close()

    async def test_malformed_json_response(self):
        """Non-JSON response body must raise MLUnavailable."""
        def handler(request):
            return httpx.Response(200, content=b"not json at all", headers={"content-type": "text/plain"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="request failed"):
                await client.score_window("sess_bad_json", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_invalid_scores_in_response(self):
        """Scores outside [0, 1] must raise MLUnavailable."""
        def handler(request):
            return httpx.Response(200, json={"spoof_score": 1.5, "evidence_quality": 0.5})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="Out-of-range"):
                await client.score_window("sess_range", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_nan_in_response_rejected(self):
        """NaN score in ML response must be rejected."""
        def handler(request):
            # httpx.Response with json= will serialize NaN as "NaN" which json.loads
            # cannot parse. We use content= with a manually crafted body.
            body = b'{"spoof_score": NaN, "evidence_quality": 0.5}'
            return httpx.Response(200, content=body, headers={"content-type": "application/json"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            # json.loads will fail on NaN (strict JSON), raising ValueError -> MLUnavailable
            with pytest.raises(MLUnavailable):
                await client.score_window("sess_nan", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_infinity_in_response_rejected(self):
        """Infinity score in ML response must be rejected."""
        def handler(request):
            body = b'{"spoof_score": Infinity, "evidence_quality": 0.5}'
            return httpx.Response(200, content=body, headers={"content-type": "application/json"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable):
                await client.score_window("sess_inf", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_connection_error(self):
        """Connection error must raise MLUnavailable."""
        def handler(request):
            raise httpx.ConnectError("connection refused")

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with pytest.raises(MLUnavailable, match="request failed"):
                await client.score_window("sess_conn", 0, SAMPLE_PCM)
        finally:
            await client.close()

    async def test_raw_audio_never_logged(self, caplog):
        """Raw PCM audio bytes must never appear in log output."""
        # Use a distinctive audio pattern that we can search for
        distinctive_pcm = b"\xDE\xAD\xBE\xEF" * 28000  # 112,000 bytes

        def handler(request):
            return _ok_response(0.5, 0.5)

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with caplog.at_level(logging.DEBUG, logger="app.services.ml_service"):
                await client.score_window("sess_privacy", 0, distinctive_pcm)
            # Ensure no log record contains the raw audio bytes or their repr
            for record in caplog.records:
                assert b"\xDE\xAD\xBE\xEF" not in record.getMessage().encode("utf-8", errors="replace")
                assert "DEADBEEF" not in record.getMessage().upper()
        finally:
            await client.close()

    async def test_raw_audio_never_logged_on_failure(self, caplog):
        """Even on ML failure, raw audio bytes must not appear in logs."""
        distinctive_pcm = b"\xCA\xFE\xBA\xBE" * 28000

        def handler(request):
            return httpx.Response(500, json={"error": "boom"})

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            with caplog.at_level(logging.DEBUG, logger="app.services.ml_service"):
                with pytest.raises(MLUnavailable):
                    await client.score_window("sess_priv_fail", 0, distinctive_pcm)
            for record in caplog.records:
                assert b"\xCA\xFE\xBA\xBE" not in record.getMessage().encode("utf-8", errors="replace")
                assert "CAFEBABE" not in record.getMessage().upper()
        finally:
            await client.close()

    async def test_configurable_endpoint(self):
        """MLClient must use the configured base_url."""
        captured_urls = []

        def handler(request):
            captured_urls.append(str(request.url))
            return _ok_response()

        transport = _make_transport(handler)
        client = MLClient(base_url="http://custom-ml:9999", timeout=5.0, transport=transport)
        try:
            await client.score_window("sess_url", 0, SAMPLE_PCM)
        finally:
            await client.close()

        assert any("custom-ml:9999" in url for url in captured_urls)
        assert any("/predict" in url for url in captured_urls)

    async def test_pcm_bytes_sent_as_body(self):
        """The raw PCM bytes are sent as the request body, not form-encoded."""
        captured_body = None

        def handler(request):
            nonlocal captured_body
            captured_body = request.content
            return _ok_response()

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        try:
            test_pcm = b"\x01\x02" * 56000
            await client.score_window("sess_body", 0, test_pcm)
        finally:
            await client.close()

        assert captured_body == b"\x01\x02" * 56000

    async def test_close_is_idempotent(self):
        """Calling close() multiple times must not raise."""
        def handler(request):
            return _ok_response()

        transport = _make_transport(handler)
        client = MLClient(base_url="http://ml-test", timeout=5.0, transport=transport)
        await client.close()
        # Second close should not raise
        await client.close()

