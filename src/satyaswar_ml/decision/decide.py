"""
Reference Decision Engine for SatyaSwar
Authoritative source: Implementation.md, Appendix D & SatyaSwar Complete Solution Document.md, Section 8.3

Maps (voice_band, voice_outcome, verification_state, action_type) to a definitive system action.
Backend owns production copy; this reference implementation guarantees behavioral alignment.
"""


from satyaswar_ml.schemas import ActionType, BandType, OutcomeType, VerificationStateType

SENSITIVE_ACTIONS: set[str] = {"money", "otp_credentials", "confidential"}


def voice_class(band: BandType, outcome: OutcomeType) -> str:
    """
    Map raw band and outcome into simplified decision categories:
    - 'uncertain': if outcome is insufficient_evidence or band is medium
    - 'high': if band is high and evidence is sufficient
    - 'low': if band is low and evidence is sufficient
    """
    if outcome == "insufficient_evidence":
        return "uncertain"
    if band == "high":
        return "high"
    if band == "medium":
        return "uncertain"
    return "low"


def decide(
    voice_band: BandType,
    voice_outcome: OutcomeType,
    verification: VerificationStateType,
    action_type: ActionType = "none",
) -> str:
    """
    Central pure decision function.
    Returns machine-readable outcome identifier.
    """
    v = voice_class(voice_band, voice_outcome)
    sensitive = action_type in SENSITIVE_ACTIONS

    # 1. Denied verification is absolute override -> likely impersonation
    if verification == "denied":
        return "likely_impersonation"

    # 2. No contact match -> cannot verify through SatyaSwar
    if verification == "no_match":
        return "cannot_verify_use_another_route"

    # 3. Confirmed verification
    if verification == "confirmed":
        if v == "high":
            # Attacker may have compromised caller or conflicting clone indicators
            return "conflicting_signals_use_second_channel"
        return "verified_normal_caution"

    # 4. High risk with pending, expired, or not_started verification
    if v == "high":
        return "hold_unverified_high_risk"

    # 5. Pending or expired verification with low or uncertain voice
    if verification in ("pending", "expired"):
        return "unverified_hold" if sensitive else "unverified_caution"

    # 6. Verification not started, low or uncertain voice
    if v == "uncertain":
        return "insufficient_evidence_verify_if_sensitive"

    # v == "low" and verification == "not_started"
    if sensitive:
        return "no_indicators_verify_before_transfer"
    return "no_indicators_not_proof"
