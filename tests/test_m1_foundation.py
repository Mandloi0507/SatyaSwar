"""
SatyaSwar - M1 Foundation Automated Tests
Tests configuration, FastAPI application setup, health check, CORS, and documentation.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client():
    """Provides a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


def test_configuration_defaults():
    """Verify that configuration loads with sensible development defaults."""
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.cors_origins == ["http://localhost:3000"]
    assert isinstance(settings.cors_origins, list)
    assert settings.ml_service_url == "http://localhost:9000"
    assert settings.audio_sample_rate == 16000
    assert settings.audio_channels == 1
    assert settings.risk_alpha == 0.4
    assert settings.verification_ttl_seconds == 120


def test_cors_origins_json_array_env():
    """Verify that JSON-array format from environment is parsed into a list."""
    with patch.dict(os.environ, {"CORS_ORIGINS": '["http://localhost:3000"]'}):
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert settings.cors_origins == ["http://localhost:3000"]


def test_cors_origins_comma_separated_env():
    """Verify that comma-separated format from environment is parsed into a list."""
    with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000"}):
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_cors_origins_unset_env():
    """Verify that default cors_origins applies when environment variable is unset."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert settings.cors_origins == ["http://localhost:3000"]


def test_get_settings_caching():
    """Verify that get_settings() returns a cached singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_app_metadata():
    """Verify basic application metadata."""
    assert app.title == "SatyaSwar API"
    assert app.version == "0.1.0"
    assert "SatyaSwar" in app.description


def test_root_endpoint(client):
    """Verify the root endpoint returns 200 with service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data == {"project": "SatyaSwar", "message": "Backend is running"}


def test_health_endpoint(client):
    """
    Verify the health endpoint returns 200 with status: healthy.
    Must not require any authentication.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_swagger_and_openapi_docs(client):
    """Verify Swagger UI and OpenAPI JSON endpoints are available."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger-ui" in docs_resp.text.lower() or "html" in docs_resp.headers.get("content-type", "")

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "SatyaSwar API"
    assert schema["info"]["version"] == "0.1.0"
    assert "/health" in schema["paths"]
    assert "/" in schema["paths"]


def test_cors_headers(client):
    """Verify CORS headers are returned for allowed origins."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_no_firebase_initialization_in_m1():
    """Verify that M1 configuration and core endpoints run without requiring Firebase credentials."""
    settings = Settings()
    assert settings.firebase_project_id == ""
    assert settings.google_application_credentials == ""

