"""
SatyaSwar - Module 6 Automated Test Suite
Risk Aggregation & Decision Engine Tests
"""

import pytest

from app.config import get_settings
from app.decision.risk_engine import (
    RiskState,
    classify_risk,
    compute_final_outcome,
    evaluate_decision,
    update_risk_state,
)
from app.models.enums import (
    ActionType,
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    VerificationStatus,
)


def test_ema_rolling_formula_known_sequence():
    """
    Verifies mathematical correctness of EMA:
    R_t = alpha * S_t + (1 - alpha) * R_{t-1}, with R_0 = S_0.
    Default alpha is 0.4.
    """
    settings = get_settings()
    alpha = settings.risk_alpha
    assert alpha == 0.4

    state = RiskState()

    # Window 0: S_0 = 0.8
    update_risk_state(state, spoof_score=0.8, evidence_quality=0.9)
    assert state.windows_total == 1
    assert state.windows_good == 1
    assert state.rolling_score == pytest.approx(0.8, rel=1e-5)
    assert state.peak_risk == pytest.approx(0.8, rel=1e-5)

    # Window 1: S_1 = 0.6 -> R_1 = 0.4 * 0.6 + 0.6 * 0.8 = 0.24 + 0.48 = 0.72
    update_risk_state(state, spoof_score=0.6, evidence_quality=0.85)
    assert state.windows_total == 2
    assert state.windows_good == 2
    assert state.rolling_score == pytest.approx(0.72, rel=1e-5)
    assert state.peak_risk == pytest.approx(0.8, rel=1e-5)

    # Window 2: S_2 = 0.4 -> R_2 = 0.4 * 0.4 + 0.6 * 0.72 = 0.16 + 0.432 = 0.592
    update_risk_state(state, spoof_score=0.4, evidence_quality=0.80)
    assert state.windows_total == 3
    assert state.windows_good == 3
    assert state.rolling_score == pytest.approx(0.592, rel=1e-5)
    assert state.peak_risk == pytest.approx(0.8, rel=1e-5)


def test_poor_evidence_ignored_by_rolling_score():
    """Windows with evidence quality below min_evidence_quality (0.5) must NOT move rolling score."""
    state = RiskState()

    # Good window establishes score 0.85
    update_risk_state(state, spoof_score=0.85, evidence_quality=0.90)
    assert state.rolling_score == pytest.approx(0.85)
    assert state.windows_good == 1

    # Poor window (unvoiced/silence/noise) with spoof 0.10, quality 0.20
    update_risk_state(state, spoof_score=0.10, evidence_quality=0.20)
    assert state.windows_total == 2
    assert state.windows_good == 1  # Not incremented
    assert state.rolling_score == pytest.approx(0.85)  # Unchanged!


def test_zero_windows_produces_unavailable():
    """A risk state with zero windows must classify as UNAVAILABLE."""
    state = RiskState()
    result = classify_risk(state, ml_available=True)
    assert result["risk_level"] == RiskLevel.UNAVAILABLE
    assert result["message_code"] == "ANALYSIS_UNAVAILABLE"
    assert result["voice_outcome"] == "unavailable"


def test_ml_unavailable_produces_unavailable():
    """When ml_available=False, output must be UNAVAILABLE even if windows exist."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.8, evidence_quality=0.9)
    result = classify_risk(state, ml_available=False)
    assert result["risk_level"] == RiskLevel.UNAVAILABLE
    assert result["message_code"] == "ANALYSIS_UNAVAILABLE"


def test_boundary_thresholds():
    """Validates categorization at exact threshold boundaries."""
    # Score 0.70 (exact high threshold) -> HIGH
    state_high = RiskState()
    update_risk_state(state_high, spoof_score=0.70, evidence_quality=0.85)
    res_high = classify_risk(state_high)
    assert res_high["risk_level"] == RiskLevel.HIGH
    assert res_high["message_code"] == "SUSPICIOUS_EVIDENCE"

    # Score 0.30 (exact low threshold) -> LOW
    state_low = RiskState()
    update_risk_state(state_low, spoof_score=0.30, evidence_quality=0.85)
    res_low = classify_risk(state_low)
    assert res_low["risk_level"] == RiskLevel.LOW
    assert res_low["message_code"] == "LOWER_SPOOF_RISK"

    # Score 0.50 (in between) -> MEDIUM
    state_med = RiskState()
    update_risk_state(state_med, spoof_score=0.50, evidence_quality=0.85)
    res_med = classify_risk(state_med)
    assert res_med["risk_level"] == RiskLevel.MEDIUM
    assert res_med["message_code"] == "UNCERTAIN"


def test_decision_case_denied():
    """Section 8.3 Row 1: Any Voice Result + Verification Denied -> Likely Impersonation."""
    # Even if voice had low spoof risk:
    state = RiskState()
    update_risk_state(state, spoof_score=0.15, evidence_quality=0.90)

    decision = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.DENIED,
        action_type=ActionType.MONEY_TRANSFER,
    )
    assert decision.final_outcome == FinalOutcome.LIKELY_IMPERSONATION
    assert decision.should_hold_action is True
    assert "Likely impersonation" in decision.headline


def test_decision_case_conflicting_signals():
    """Section 8.3 Row 2: High Voice Risk + Verification Confirmed -> Conflicting Signals."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.92, evidence_quality=0.95)

    decision = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.APPROVED,
        action_type=ActionType.MONEY_TRANSFER,
    )
    assert decision.final_outcome == FinalOutcome.CONFLICTING_SIGNALS
    assert decision.should_hold_action is True
    assert "Conflicting signals" in decision.headline


def test_decision_case_low_risk_confirmed():
    """Section 8.3 Row 3: Low or Uncertain Risk + Verification Confirmed -> Likely Genuine."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.18, evidence_quality=0.90)

    decision = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.APPROVED,
        action_type=ActionType.MONEY_TRANSFER,
    )
    assert decision.final_outcome == FinalOutcome.LIKELY_GENUINE
    assert decision.should_hold_action is False
    assert "Verified through the linked account" in decision.headline


def test_decision_case_high_risk_unverified():
    """Section 8.3 Row 4: High Voice Risk + Pending/Expired -> Unverified High Risk."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.88, evidence_quality=0.90)

    for status in (VerificationStatus.PENDING, VerificationStatus.EXPIRED, VerificationStatus.NOT_REQUESTED):
        decision = evaluate_decision(
            state=state,
            verification_status=status,
            action_type=ActionType.OTP_CREDENTIALS,
        )
        assert decision.final_outcome == FinalOutcome.LIKELY_IMPERSONATION
        assert decision.should_hold_action is True
        assert "Unverified, high risk" in decision.headline


def test_decision_case_no_contact_match():
    """Section 8.3 Row 5: Any Voice Result + No Contact Match -> Cannot Verify."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.25, evidence_quality=0.85)

    decision = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.NO_CONTACT_MATCH,
        action_type=ActionType.MONEY_TRANSFER,
    )
    assert "Cannot verify through SatyaSwar" in decision.headline
    assert decision.should_hold_action is True  # Sensitive action held


def test_decision_case_uncertain_not_started():
    """Section 8.3 Row 6: Uncertain Risk + Verification Not Started -> Insufficient Evidence."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.50, evidence_quality=0.85)

    decision = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.NOT_REQUESTED,
        action_type=ActionType.CONFIDENTIAL_INFO,
    )
    assert decision.final_outcome == FinalOutcome.INSUFFICIENT_EVIDENCE
    assert decision.should_hold_action is True
    assert "Insufficient evidence" in decision.headline


def test_action_type_sensitivity():
    """
    Verifies that low risk with unverified contact holds action for sensitive requests
    (money_transfer, otp_credentials) but allows non-sensitive 'other' actions.
    """
    state = RiskState()
    update_risk_state(state, spoof_score=0.20, evidence_quality=0.90)

    # Financial action -> must hold until verified
    dec_money = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.NOT_REQUESTED,
        action_type=ActionType.MONEY_TRANSFER,
    )
    assert dec_money.should_hold_action is True

    # Casual/other action -> does not strictly hold
    dec_other = evaluate_decision(
        state=state,
        verification_status=VerificationStatus.NOT_REQUESTED,
        action_type=ActionType.OTHER,
    )
    assert dec_other.should_hold_action is False


def test_compute_final_outcome_helper():
    """Verifies convenience function compute_final_outcome returns valid FinalOutcome enums."""
    state = RiskState()
    update_risk_state(state, spoof_score=0.85, evidence_quality=0.90)
    outcome = compute_final_outcome(state, VerificationStatus.NOT_REQUESTED)
    assert isinstance(outcome, FinalOutcome)
    assert outcome == FinalOutcome.LIKELY_IMPERSONATION

