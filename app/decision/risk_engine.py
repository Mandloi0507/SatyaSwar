"""
SatyaSwar - Risk Aggregation & Decision Engine
Member 2: Backend, Infrastructure, Database and Security

Provides stateful exponential moving average (EMA) score aggregation and
risk level classification based on audio evidence quality and spoof scores.
Implements the finalized Decision Function mapping voice analysis, trusted contact
verification states, and contextual action types into definitive security decisions.
"""

from dataclasses import dataclass
from typing import Any, Optional, Union

from app.config import get_settings
from app.models.enums import (
    ActionType,
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    VerificationStatus,
)


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


@dataclass
class DecisionEvaluation:
    """Structured decision output mapping voice risk, verification status, and action type."""

    final_outcome: FinalOutcome
    voice_outcome: str  # likely_genuine | suspicious | insufficient_evidence | unavailable
    verification_status: VerificationStatus
    action_type: ActionType
    headline: str
    recommendation: str
    should_hold_action: bool
    risk_score: Optional[float]
    risk_level: RiskLevel
    evidence_quality: EvidenceQualityLevel


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


def normalize_verification_status(status: Union[VerificationStatus, str]) -> VerificationStatus:
    """Normalizes various string representations of verification status."""
    if isinstance(status, VerificationStatus):
        return status
    s = str(status).strip().upper()
    if s in ("CONFIRMED", "APPROVED"):
        return VerificationStatus.APPROVED
    if s in ("DENIED", "REJECTED"):
        return VerificationStatus.DENIED
    if s in ("PENDING",):
        return VerificationStatus.PENDING
    if s in ("EXPIRED",):
        return VerificationStatus.EXPIRED
    if s in ("CANCELLED",):
        return VerificationStatus.CANCELLED
    if s in ("NO_CONTACT_MATCH", "NO_MATCH"):
        return VerificationStatus.NO_CONTACT_MATCH
    return VerificationStatus.NOT_REQUESTED


def normalize_action_type(action: Union[ActionType, str]) -> ActionType:
    """Normalizes various string representations of requested action."""
    if isinstance(action, ActionType):
        return action
    s = str(action).strip().lower()
    for item in ActionType:
        if item.value == s:
            return item
    return ActionType.OTHER


def evaluate_decision(
    state: RiskState,
    verification_status: Union[VerificationStatus, str] = VerificationStatus.NOT_REQUESTED,
    action_type: Union[ActionType, str] = ActionType.OTHER,
    ml_available: bool = True,
) -> DecisionEvaluation:
    """
    Final decision function implementing Section 8.3 of the Complete Solution Document.

    Combines voice analysis outcome, trusted-contact verification state, and the
    requested action type (e.g. money transfer, OTP credentials) into a structured decision.

    Guarantees:
    - Zero trust: A verified identity does not downgrade high voice risk to safe.
    - Sensitive actions (money transfers, OTPs) are held on any suspicious or unverified signal.
    """
    v_status = normalize_verification_status(verification_status)
    a_type = normalize_action_type(action_type)
    classification = classify_risk(state, ml_available=ml_available)

    risk_level: RiskLevel = classification["risk_level"]
    risk_score: Optional[float] = classification["risk_score"]
    evidence_qual: EvidenceQualityLevel = classification["evidence_quality"]
    voice_outcome: str = classification["voice_outcome"]

    is_sensitive_action = a_type in (
        ActionType.MONEY_TRANSFER,
        ActionType.OTP_CREDENTIALS,
        ActionType.CONFIDENTIAL_INFO,
    )

    # --------------------------------------------------------------------------
    # Case 1: Verification DENIED by trusted contact (Row 1)
    # --------------------------------------------------------------------------
    if v_status == VerificationStatus.DENIED:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.LIKELY_IMPERSONATION,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Likely impersonation. Do not proceed.",
            recommendation="The claimed contact explicitly denied being on this call. Do not transfer funds or disclose credentials.",
            should_hold_action=True,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 2: High Voice Risk + Verification CONFIRMED / APPROVED (Row 2)
    # --------------------------------------------------------------------------
    if risk_level == RiskLevel.HIGH and v_status == VerificationStatus.APPROVED:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.CONFLICTING_SIGNALS,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Conflicting signals. Use a second channel before any sensitive action.",
            recommendation="High synthetic voice indicators detected despite trusted contact confirmation. Call back directly on a known number before proceeding.",
            should_hold_action=True,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 3: Low or Uncertain Risk + Verification CONFIRMED / APPROVED (Row 3)
    # --------------------------------------------------------------------------
    if v_status == VerificationStatus.APPROVED:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.LIKELY_GENUINE,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Verified through the linked account. Normal caution.",
            recommendation="Caller identity verified via independent trusted-contact confirmation. Exercise standard vigilance.",
            should_hold_action=False,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 4: High Voice Risk + Pending, Expired, or Not Requested (Row 4)
    # --------------------------------------------------------------------------
    if risk_level == RiskLevel.HIGH:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.LIKELY_IMPERSONATION,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Unverified, high risk. Hold the sensitive action.",
            recommendation="High synthetic voice probability detected and identity is unverified. Hold all requests for money, OTPs, or confidential information.",
            should_hold_action=True,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 5: No Contact Match (Row 5)
    # --------------------------------------------------------------------------
    if v_status == VerificationStatus.NO_CONTACT_MATCH:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.INSUFFICIENT_EVIDENCE if risk_level != RiskLevel.HIGH else FinalOutcome.SUSPICIOUS,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Cannot verify through SatyaSwar. Use another route.",
            recommendation="Caller does not match any registered trusted contact. Call the person back on a known, verified phone number.",
            should_hold_action=is_sensitive_action,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 6: ML Unavailable (Row 6)
    # --------------------------------------------------------------------------
    if not ml_available or risk_level == RiskLevel.UNAVAILABLE:
        return DecisionEvaluation(
            final_outcome=FinalOutcome.UNAVAILABLE,
            voice_outcome="unavailable",
            verification_status=v_status,
            action_type=a_type,
            headline="Voice analysis temporarily unavailable.",
            recommendation="Speech analysis is currently offline. Verify caller identity independently before taking sensitive actions.",
            should_hold_action=is_sensitive_action,
            risk_score=None,
            risk_level=RiskLevel.UNAVAILABLE,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 7: Uncertain / Inconclusive Risk + Not Started (Row 7)
    # --------------------------------------------------------------------------
    if risk_level in (RiskLevel.INCONCLUSIVE, RiskLevel.MEDIUM):
        return DecisionEvaluation(
            final_outcome=FinalOutcome.INSUFFICIENT_EVIDENCE,
            voice_outcome=voice_outcome,
            verification_status=v_status,
            action_type=a_type,
            headline="Insufficient evidence. Verify if the request is sensitive.",
            recommendation="Voice evidence is inconclusive. Initiate independent contact verification if funds or credentials are requested.",
            should_hold_action=is_sensitive_action,
            risk_score=risk_score,
            risk_level=risk_level,
            evidence_quality=evidence_qual,
        )

    # --------------------------------------------------------------------------
    # Case 8: Low Risk + Not Started (Row 8)
    # --------------------------------------------------------------------------
    return DecisionEvaluation(
        final_outcome=FinalOutcome.LIKELY_GENUINE,
        voice_outcome=voice_outcome,
        verification_status=v_status,
        action_type=a_type,
        headline="No synthetic indicators found. Verify before transfers.",
        recommendation="Lower spoof risk detected. Note: this is not proof of identity; verify with the trusted contact before transferring money.",
        should_hold_action=is_sensitive_action,
        risk_score=risk_score,
        risk_level=RiskLevel.LOW,
        evidence_quality=evidence_qual,
    )


def compute_final_outcome(
    state: RiskState,
    verification_status: Union[VerificationStatus, str] = VerificationStatus.NOT_REQUESTED,
    action_type: Union[ActionType, str] = ActionType.OTHER,
    ml_available: bool = True,
) -> FinalOutcome:
    """Convenience wrapper returning strictly the FinalOutcome enum."""
    eval_result = evaluate_decision(
        state=state,
        verification_status=verification_status,
        action_type=action_type,
        ml_available=ml_available,
    )
    return eval_result.final_outcome
