"""
Export JSON Schema and OpenAPI specifications for the SatyaSwar contract.
Authoritative source: Implementation.md, Section 4, 6.4, 6.5.

Outputs:
- docs/events.schema.json
- docs/openapi.json
"""

import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from satyaswar_ml.adapters.ws_app import app
from satyaswar_ml.schemas import (
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


def export_schemas() -> None:
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export events & message schema
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
    _, top_level_schema = models_json_schema(
        [(m, "validation") for m in models],
        title="SatyaSwarContractEvents",
        description="Comprehensive JSON Schema for SatyaSwar Integration Contract Events",
    )

    # Add union references for easy validation
    events_schema_path = docs_dir / "events.schema.json"
    with open(events_schema_path, "w", encoding="utf-8") as f:
        json.dump(top_level_schema, f, indent=2)
    print(f"Exported events JSON Schema to {events_schema_path}")

    # 2. Export OpenAPI specification
    openapi_spec = app.openapi()
    openapi_path = docs_dir / "openapi.json"
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, indent=2)
    print(f"Exported OpenAPI spec to {openapi_path}")


if __name__ == "__main__":
    export_schemas()
