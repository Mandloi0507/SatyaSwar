"""
SatyaSwar AI/ML Subsystem
Voice integrity and voice-cloning impersonation risk analysis engine.
SIH 2026, Problem Statement 26104.
"""

from satyaswar_ml.config import SatyaSwarConfig, load_config
from satyaswar_ml.decision.decide import decide, voice_class
from satyaswar_ml.schemas import (
    SCHEMA_VERSION,
    AlertEvent,
    CallSummaryEvent,
    ClaimEvent,
    ConfigUpdateMessage,
    Contact,
    ContextEvent,
    ErrorEvent,
    InfoEvent,
    SatyaSwarEvent,
    ScoreEvent,
    SessionEndMessage,
    SessionReadyEvent,
    SessionStartMessage,
    TranscriptEvent,
)

__version__ = "1.0.0"

__all__ = [
    "SCHEMA_VERSION",
    "AlertEvent",
    "CallSummaryEvent",
    "ClaimEvent",
    "ConfigUpdateMessage",
    "Contact",
    "ContextEvent",
    "ErrorEvent",
    "InfoEvent",
    "SatyaSwarConfig",
    "SatyaSwarEvent",
    "ScoreEvent",
    "SessionEndMessage",
    "SessionReadyEvent",
    "SessionStartMessage",
    "TranscriptEvent",
    "decide",
    "load_config",
    "voice_class",
]
