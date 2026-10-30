"""
SatyaSwar Integration Contract Schemas
Authoritative source: Implementation.md, Section 6.4

All messages carry schema_version ("1.0") and type.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

BandType = Literal["low", "medium", "high", "insufficient"]
OutcomeType = Literal["likely_genuine", "suspicious", "insufficient_evidence"]
QualityLabelType = Literal["good", "fair", "poor"]
ContextCategoryType = Literal[
    "urgency",
    "secrecy",
    "money",
    "otp_credentials",
    "authority",
    "family_emergency",
]
ActionType = Literal["money", "otp_credentials", "confidential", "other", "none"]
VerificationStateType = Literal[
    "not_started",
    "pending",
    "confirmed",
    "denied",
    "expired",
    "no_match",
]


class BaseContractModel(BaseModel):
    """Base model enforcing contract conventions."""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )


# -----------------------------------------------------------------------------
# Upstream Messages (Client / Backend -> ML)
# -----------------------------------------------------------------------------

class Contact(BaseContractModel):
    """Contact representation for claimed-identity matching."""
    contact_id: str = Field(..., description="Unique contact identifier (e.g. UID)")
    display_name: str = Field(..., description="Full display name (Latin or Devanagari)")
    aliases: list[str] = Field(default_factory=list, description="Alternative names / nicknames")
    label: str | None = Field(default=None, description="Relationship or disambiguation label (e.g. 'Sister')")


class SessionStartMessage(BaseContractModel):
    """Message sent by client or backend to initialise a call session."""
    schema_version: str = Field(default=SCHEMA_VERSION, description="Contract schema version")
    type: Literal["session_start"] = "session_start"
    call_id: str = Field(..., description="Unique call identifier")
    mode: Literal["chunks", "windows"] = Field(
        default="chunks",
        description="Chunk mode (1.75s non-overlapping) or Window mode (3.5s overlapping)",
    )
    language_hint: str | None = Field(default=None, description="Optional ISO language hint (e.g. 'hi', 'en')")
    telephony_profile: str = Field(default="none", description="Telephony degradation profile to apply")
    contacts: list[Contact] = Field(default_factory=list, description="Caller's contact list for identity matching")
    resume: bool = Field(default=False, description="True if reconnecting to an existing session within 60s")


class ConfigUpdateMessage(BaseContractModel):
    """Dynamic configuration update during an active call."""
    schema_version: str = Field(default=SCHEMA_VERSION, description="Contract schema version")
    type: Literal["config_update"] = "config_update"
    telephony_profile: str | None = Field(default=None, description="Update telephony profile (e.g. 'g711_ulaw')")


class SessionEndMessage(BaseContractModel):
    """Signal session termination."""
    schema_version: str = Field(default=SCHEMA_VERSION, description="Contract schema version")
    type: Literal["session_end"] = "session_end"


ClientMessage = Annotated[
    SessionStartMessage | ConfigUpdateMessage | SessionEndMessage,
    Field(discriminator="type"),
]


# -----------------------------------------------------------------------------
# Downstream Event Sub-models
# -----------------------------------------------------------------------------

class WindowBounds(BaseContractModel):
    start_ms: int = Field(..., ge=0, description="Start offset of window in call audio (ms)")
    end_ms: int = Field(..., ge=0, description="End offset of window in call audio (ms)")


class EvidenceModel(BaseContractModel):
    """Measurements supporting score reliability."""
    speech_seconds: float = Field(..., ge=0.0, description="Active speech duration in window (seconds)")
    snr_db: float = Field(..., description="Estimated signal-to-noise ratio in dB")
    agreement: float = Field(..., ge=0.0, le=1.0, description="Score consistency or inter-model agreement [0, 1]")
    quality: float = Field(..., ge=0.0, le=1.0, description="Combined evidence quality score [0, 1]")
    quality_label: QualityLabelType = Field(..., description="Discrete evidence quality rating")

    # Critical requirement: distinguish synthetic-voice evidence from replay-attack evidence
    synthetic_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Dedicated synthetic voice probability [0, 1]"
    )
    replay_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Dedicated replay / physical attack indicator [0, 1]"
    )
    replay_detected: bool | None = Field(
        default=None, description="Flag indicating presentation/replay attack detected"
    )


class LanguageModel(BaseContractModel):
    code: str | None = Field(default=None, description="Detected ISO language code ('hi', 'en' or null)")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Detection confidence")
    source: str | None = Field(default=None, description="Detection source (e.g. 'asr', 'hint')")


class LatencyBreakdown(BaseContractModel):
    decode: float = Field(default=0.0, ge=0.0, description="Audio decode latency (ms)")
    telephony: float = Field(default=0.0, ge=0.0, description="Telephony filtering latency (ms)")
    vad: float = Field(default=0.0, ge=0.0, description="VAD & SNR latency (ms)")
    detector: float = Field(default=0.0, ge=0.0, description="Model inference latency (ms)")
    total: float = Field(default=0.0, ge=0.0, description="End-to-end window processing latency (ms)")


class ModelMeta(BaseContractModel):
    name: str = Field(..., description="Model identifier (e.g. 'xlsr300m_aasist_ft')")
    version: str = Field(..., description="Model checkpoint or release version")


class WhyItem(BaseContractModel):
    """
    Computed, auditable explanation item.
    NOTE: Free-form text explanations are strictly forbidden by AGENTS.md.
    """
    kind: str = Field(
        ...,
        description=(
            "Computed metric kind (e.g. 'window_score', 'speech_seconds', 'snr_db', "
            "'model_agreement', 'synthetic_score', 'replay_score', 'supporting_heuristic')"
        ),
    )
    text_key: str | None = Field(default=None, description="Localization key for UI rendering")
    value: float | int | str | bool = Field(..., description="Exact computed measurement")


class BilingualText(BaseContractModel):
    en: str = Field(..., description="English text or audio key")
    hi: str = Field(..., description="Hindi text or audio key")


class ContextFlag(BaseContractModel):
    category: ContextCategoryType = Field(..., description="Scam context risk category")
    term: str = Field(..., description="Matched keyword or phrase")
    language: str = Field(..., description="Source language ('en', 'hi_latin', 'hi_deva')")
    at_ms: int = Field(..., ge=0, description="Timestamp offset where keyword was spotted (ms)")


class ClaimCandidate(BaseContractModel):
    contact_id: str = Field(..., description="Matched contact ID")
    matched_on: str = Field(..., description="Display name, alias, or transcript token that matched")
    score: float = Field(..., ge=0.0, le=100.0, description="Fuzzy match similarity score [0, 100]")
    rank: int = Field(..., ge=1, description="Rank among returned candidates (1 = top)")


# -----------------------------------------------------------------------------
# Downstream Event Messages (ML -> Client / Backend / Dashboard)
# -----------------------------------------------------------------------------

class SessionReadyEvent(BaseContractModel):
    """Emitted after session_start when engine has prepared buffers and warm-up."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["session_ready"] = "session_ready"
    call_id: str
    model: dict[str, Any] = Field(..., description="Active model metadata")
    device: str = Field(..., description="Compute device ('cuda:0', 'cpu', etc.)")
    warmup_ms: float = Field(..., ge=0.0, description="Warm-up execution time in ms")
    contacts_loaded: int = Field(..., ge=0, description="Number of contacts indexed for matching")


class ScoreEvent(BaseContractModel):
    """
    Emitted after first 3.5s of audio, then every 1.75s hop.
    Primary voice authenticity signal.
    """
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["score"] = "score"
    call_id: str
    window_index: int = Field(..., ge=0, description="Monotonically increasing window index")
    window: WindowBounds
    spoof_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Raw spoof probability [0, 1], higher = more likely synthetic. Null on insufficient evidence.",
    )
    smoothed_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Evidence-weighted EMA smoothed score. Null on insufficient evidence.",
    )
    band: BandType = Field(..., description="Current risk band")
    previous_band: BandType | None = Field(default=None, description="Previous committed risk band")
    band_changed: bool = Field(default=False, description="True if hysteresis committed a band transition")
    outcome: OutcomeType = Field(..., description="Three-way decision outcome")
    evidence: EvidenceModel
    language: LanguageModel
    telephony_profile: str = Field(default="none")
    latency_ms: LatencyBreakdown
    client_ts_ms: int | None = Field(default=None, description="Client timestamp from binary frame header")
    server_recv_ts_ms: int | None = Field(default=None, description="Server receipt timestamp")
    server_send_ts_ms: int | None = Field(default=None, description="Server dispatch timestamp")
    model: ModelMeta
    why: list[WhyItem] = Field(default_factory=list, description="Auditable computed measurement signals")
    mock: bool = Field(default=False, description="True ONLY when generated by mock engine")


class TranscriptEvent(BaseContractModel):
    """Emitted for early speech transcription off the critical scoring path."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["transcript"] = "transcript"
    call_id: str
    text: str = Field(..., description="Transcribed speech text (dropped after dispatch)")
    language: str = Field(..., description="Detected language code ('en' or 'hi')")
    is_final: bool = Field(default=False, description="True when 12s speech window transcription completes")
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., ge=0)


class ContextEvent(BaseContractModel):
    """Emitted when context keyword rules match transcript tokens."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["context"] = "context"
    call_id: str
    flags: list[ContextFlag] = Field(..., min_length=1, description="Detected scam context signals")


class ClaimEvent(BaseContractModel):
    """
    Ranked suggested matches from caller contact list.
    NOTE: Never auto-selects; suggestions only.
    """
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["claim"] = "claim"
    call_id: str
    candidates: list[ClaimCandidate] = Field(default_factory=list)
    ambiguous: bool = Field(default=False, description="True if top candidates are close or share tokens")
    no_match: bool = Field(default=False, description="True if no contact exceeded similarity threshold")


class AlertEvent(BaseContractModel):
    """Emitted only on committed band transitions with hysteresis."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["alert"] = "alert"
    call_id: str
    level: BandType = Field(..., description="Alert severity level")
    reason_code: str = Field(..., description="Auditable reason code (e.g. 'band_escalated_high')")
    text: BilingualText = Field(..., description="Localized alert strings for UI display")
    audio_key: BilingualText = Field(..., description="Audio file identifiers for voice prompt playback")


class InfoEvent(BaseContractModel):
    """Operational advisory event (e.g. dropped windows, ASR unavailable)."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["info"] = "info"
    call_id: str | None = None
    code: str = Field(..., description="Machine-readable info code (e.g. 'windows_dropped')")
    message: str = Field(..., description="Descriptive status message")


class ErrorEvent(BaseContractModel):
    """Error event emitted on framing or runtime failure."""
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["error"] = "error"
    call_id: str | None = None
    code: str = Field(..., description="Error code (e.g. 'bad_frame', 'model_error')")
    message: str = Field(..., description="Error detail")
    recoverable: bool = Field(default=True, description="Whether the session can continue")


class CallSummaryEvent(BaseContractModel):
    """
    Summary emitted at session close.
    Carries scores and timing metrics only. Audio and transcripts are strictly omitted.
    """
    schema_version: str = Field(default=SCHEMA_VERSION)
    type: Literal["call_summary"] = "call_summary"
    call_id: str
    peak_score: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_score: float | None = Field(default=None, ge=0.0, le=1.0)
    final_band: BandType
    final_outcome: OutcomeType
    time_in_band_s: dict[str, float] = Field(
        ..., description="Seconds spent in each risk band: low, medium, high, insufficient"
    )
    evidence_quality_mean: float = Field(..., ge=0.0, le=1.0)
    languages_seen: list[str] = Field(default_factory=list)
    context_categories: list[str] = Field(default_factory=list)
    windows_scored: int = Field(..., ge=0)
    windows_insufficient: int = Field(..., ge=0)
    latency_ms: dict[str, float] = Field(..., description="Latency statistics (e.g. p50, p95)")
    mock: bool = Field(default=False)


# -----------------------------------------------------------------------------
# REST Endpoint Models (Implementation.md, Section 6.5)
# -----------------------------------------------------------------------------

class HealthResponse(BaseContractModel):
    status: Literal["ok", "degraded", "error"] = "ok"
    model_loaded: bool = Field(..., description="Whether detection model is loaded and ready")
    device: str = Field(..., description="Device string ('cuda:0', 'cpu', etc.)")
    versions: dict[str, str] = Field(..., description="Versions of satyaswar_ml, torch, whisper, etc.")
    warmup_ms: float = Field(..., ge=0.0, description="Warm-up latency in milliseconds")
    mock: bool = Field(..., description="True if running in mock mode")


class ModelInfoResponse(BaseContractModel):
    model_name: str
    version: str
    thresholds: dict[str, Any]
    languages_evaluated: list[str]


class ContactsMatchRequest(BaseContractModel):
    text: str = Field(..., description="Transcript text to match contacts against")
    contacts: list[Contact] = Field(..., description="Candidate contact list")


SatyaSwarEvent = Annotated[
    SessionReadyEvent | ScoreEvent | TranscriptEvent | ContextEvent | ClaimEvent | AlertEvent | InfoEvent | ErrorEvent | CallSummaryEvent,
    Field(discriminator="type"),
]

