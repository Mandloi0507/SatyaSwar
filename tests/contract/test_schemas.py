"""
Contract validation tests for SatyaSwar ML integration schemas.
Authoritative source: Implementation.md, Section 6.4, 15.2
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic.json_schema import models_json_schema

from satyaswar_ml.adapters.ws_app import app
from satyaswar_ml.schemas import (
    SCHEMA_VERSION,
    AlertEvent,
    CallSummaryEvent,
    ClaimEvent,
    ConfigUpdateMessage,
    ContextEvent,
    ErrorEvent,
    InfoEvent,
    ScoreEvent,
    SessionEndMessage,
    SessionReadyEvent,
    SessionStartMessage,
    TranscriptEvent,
)

FIXTURES_DIR = Path(__file__).parent.parent.parent / "assets" / "fixtures" / "events"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


class TestEventFixtures:
    """Verify that every fixture in assets/fixtures/events is strictly valid."""

    @pytest.mark.parametrize(
        "filename,model_cls",
        [
            ("session_start.json", SessionStartMessage),
            ("config_update.json", ConfigUpdateMessage),
            ("session_end.json", SessionEndMessage),
            ("session_ready.json", SessionReadyEvent),
            ("score.json", ScoreEvent),
            ("transcript.json", TranscriptEvent),
            ("context.json", ContextEvent),
            ("claim.json", ClaimEvent),
            ("alert.json", AlertEvent),
            ("info.json", InfoEvent),
            ("error.json", ErrorEvent),
            ("call_summary.json", CallSummaryEvent),
        ],
    )
    def test_fixtures_parse_and_roundtrip(self, filename: str, model_cls: type):
        fixture_path = FIXTURES_DIR / filename
        assert fixture_path.is_file(), f"Missing fixture file: {fixture_path}"

        with open(fixture_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # 1. Validate with target model
        instance = model_cls.model_validate(raw_data)
        assert instance.schema_version == SCHEMA_VERSION

        # 2. Re-serialise and verify roundtrip fidelity
        reloaded = model_cls.model_validate_json(instance.model_dump_json())
        assert reloaded == instance

    def test_score_event_replay_and_synthetic_distinction(self):
        """Verify that synthetic and replay attack evidence are cleanly distinguishable."""
        fixture_path = FIXTURES_DIR / "score.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        score_ev = ScoreEvent.model_validate(data)
        assert score_ev.evidence.synthetic_score is not None
        assert score_ev.evidence.replay_score is not None
        assert score_ev.evidence.replay_detected is False

        # Ensure why items can carry distinct synthetic and replay markers
        kinds = [w.kind for w in score_ev.why]
        assert "synthetic_score" in kinds
        assert "replay_score" in kinds


class TestSchemaIntegrityAndDrift:
    """Ensure that the committed JSON Schema and OpenAPI doc match the active code."""

    def test_events_schema_not_drifted(self):
        schema_path = DOCS_DIR / "events.schema.json"
        assert schema_path.is_file(), "docs/events.schema.json is missing!"

        models = [
            SessionStartMessage,
            ConfigUpdateMessage,
            SessionEndMessage,
            SessionReadyEvent,
            ScoreEvent,
            TranscriptEvent,
            ContextEvent,
            ClaimEvent,
            AlertEvent,
            InfoEvent,
            ErrorEvent,
            CallSummaryEvent,
        ]
        _, current_schema = models_json_schema(
            [(m, "validation") for m in models],
            title="SatyaSwarContractEvents",
            description="Comprehensive JSON Schema for SatyaSwar Integration Contract Events",
        )

        with open(schema_path, "r", encoding="utf-8") as f:
            committed_schema = json.load(f)

        assert committed_schema == current_schema, (
            "Committed docs/events.schema.json differs from current Pydantic models! "
            "Run 'python scripts/export_schemas.py' to synchronise."
        )

    def test_openapi_spec_not_drifted(self):
        openapi_path = DOCS_DIR / "openapi.json"
        assert openapi_path.is_file(), "docs/openapi.json is missing!"

        with open(openapi_path, "r", encoding="utf-8") as f:
            committed_openapi = json.load(f)

        current_openapi = app.openapi()
        assert committed_openapi == current_openapi, (
            "Committed docs/openapi.json differs from current FastAPI routes! "
            "Run 'python scripts/export_schemas.py' to synchronise."
        )


class TestValidationEdgeCases:
    """Check contract enforcement on invalid inputs."""

    def test_score_event_negative_latency_rejected(self):
        with open(FIXTURES_DIR / "score.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["latency_ms"]["detector"] = -10.0
        with pytest.raises(ValidationError):
            ScoreEvent.model_validate(data)

    def test_score_event_invalid_band_rejected(self):
        with open(FIXTURES_DIR / "score.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["band"] = "critical_danger"  # Invalid band enum
        with pytest.raises(ValidationError):
            ScoreEvent.model_validate(data)

    def test_score_event_invalid_outcome_rejected(self):
        with open(FIXTURES_DIR / "score.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["outcome"] = "guaranteed_fake"  # Invalid outcome enum
        with pytest.raises(ValidationError):
            ScoreEvent.model_validate(data)

    def test_extra_fields_forbidden(self):
        with open(FIXTURES_DIR / "session_start.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["unauthorized_injected_field"] = "malicious_payload"
        with pytest.raises(ValidationError):
            SessionStartMessage.model_validate(data)
