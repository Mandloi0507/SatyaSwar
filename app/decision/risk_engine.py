"""
SatyaSwar - Risk Aggregation & Decision Engine
Member 2: Backend, Infrastructure, Database and Security

Provides stateful exponential moving average (EMA) score aggregation and
risk level classification based on audio evidence quality and spoof scores.
"""

from dataclasses import dataclass
from typing import Any, Optional

from app.config import get_settings
from app.models.enums import EvidenceQualityLevel, FinalOutcome, RiskLevel


@dataclass
class RiskState:
    """Stateful accumulator tracking per-call audio analysis windows and rolling risk."""

    rolling_score: Optional[float] = None
    windows_total: int = 0
    windows_good: int = 0
    latest_evidence: float = 0.0
    latest_spoof: Optional[float] = None
    peak_risk: Optional[float] = None
    ml_failures_in_row: int = 0


def update_risk_state(
    state: RiskState,
    spoof_score: float,
    evidence_quality: float,
) -> RiskState:
    """
    Updates the rolling risk state using an Exponential Moving Average (EMA):
        R_t = alpha * S_t + (1 - alpha) * R_{t-1}
        with R_0 = S_0.

    Windows with evidence quality below `min_evidence_quality` do not modify the rolling
    score, preventing unvoiced background noise or silence from corrupting analysis.
    """
    settings = get_settings()
    state.windows_total += 1
    state.latest_evidence = evidence_quality
    state.latest_spoof = spoof_score
    state.ml_failures_in_row = 0

    if evidence_quality >= settings.min_evidence_quality:
        state.windows_good += 1
        if state.rolling_score is None:
            state.rolling_score = spoof_score
        else:
            alpha = settings.risk_alpha
            state.rolling_score = (alpha * spoof_score) + ((1.0 - alpha) * state.rolling_score)

        if state.peak_risk is None or state.rolling_score > state.peak_risk:
            state.peak_risk = state.rolling_score

    return state


def classify_risk(state: RiskState, ml_available: bool = True) -> dict[str, Any]:
    """
    Maps current risk accumulator state to standardized categorical risk levels,
    evidence quality tiers, and client-facing response messages.

    Guarantees:
    - Never defaults to 'safe' or 'LOW' when ML is unavailable or evidence is missing.
    - Uses calibrated terminology ('lower spoof risk' instead of 'guaranteed genuine').
    """
    settings = get_settings()

    # Determine evidence quality enum
    if state.latest_evidence >= 0.8:
        quality_level = EvidenceQualityLevel.GOOD
    elif state.latest_evidence >= settings.min_evidence_quality:
        quality_level = EvidenceQualityLevel.LIMITED
    else:
        quality_level = EvidenceQualityLevel.POOR

    if not ml_available or state.windows_total == 0:
        return {
            "risk_level": RiskLevel.UNAVAILABLE,
            "message_code": "ANALYSIS_UNAVAILABLE",
            "risk_score": None,
            "evidence_quality": quality_level,
            "voice_outcome": "unavailable",
            "is_available": False,
        }

    if state.rolling_score is None or quality_level == EvidenceQualityLevel.POOR:
        return {
            "risk_level": RiskLevel.INCONCLUSIVE,
            "message_code": "INSUFFICIENT_EVIDENCE",
            "risk_score": state.rolling_score,
            "evidence_quality": quality_level,
            "voice_outcome": "insufficient_evidence",
            "is_available": True,
        }

    score = state.rolling_score
    if score >= settings.risk_high_threshold:
        level = RiskLevel.HIGH
        code = "SUSPICIOUS_EVIDENCE"
        outcome = "suspicious"
    elif score <= settings.risk_low_threshold:
        level = RiskLevel.LOW
        code = "LOWER_SPOOF_RISK"
        outcome = "likely_genuine"
    else:
        level = RiskLevel.MEDIUM
        code = "UNCERTAIN"
        outcome = "suspicious"

    return {
        "risk_level": level,
        "message_code": code,
        "risk_score": round(score, 4),
        "evidence_quality": quality_level,
        "voice_outcome": outcome,
        "is_available": True,
    }


def compute_final_outcome(
    state: RiskState,
    verification_status: str,
    ml_available: bool = True,
) -> FinalOutcome:
    """
    Evaluates final call outcome incorporating voice risk and independent verification.
    """
    classification = classify_risk(state, ml_available=ml_available)
    risk_level = classification["risk_level"]

    if risk_level == RiskLevel.UNAVAILABLE:
        return FinalOutcome.UNAVAILABLE
    if risk_level == RiskLevel.INCONCLUSIVE:
        return FinalOutcome.INSUFFICIENT_EVIDENCE
    if risk_level == RiskLevel.HIGH:
        return FinalOutcome.LIKELY_IMPERSONATION
    if risk_level == RiskLevel.LOW:
        return FinalOutcome.LIKELY_GENUINE
    return FinalOutcome.SUSPICIOUS
