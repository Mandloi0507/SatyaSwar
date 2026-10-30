"""
Unit & Contract tests for SatyaSwar reference decision function.
Authoritative source: Implementation.md, Appendix D & SatyaSwar Complete Solution Document.md, Section 8.3
"""

import pytest

from satyaswar_ml.decision.decide import decide, voice_class


class TestDecisionTableRows:
    """Verify all table rows in Appendix D and Solution Document Section 8.3."""

    # 1. Denied verification is absolute override -> likely_impersonation
    @pytest.mark.parametrize("band", ["low", "medium", "high", "insufficient"])
    @pytest.mark.parametrize("outcome", ["likely_genuine", "suspicious", "insufficient_evidence"])
    @pytest.mark.parametrize("action", ["none", "money", "otp_credentials", "confidential", "other"])
    def test_verification_denied_overrides_everything(self, band, outcome, action):
        res = decide(band, outcome, "denied", action)
        assert res == "likely_impersonation"

    # 2. No contact match -> cannot verify through SatyaSwar
    @pytest.mark.parametrize("band", ["low", "medium", "high", "insufficient"])
    @pytest.mark.parametrize("outcome", ["likely_genuine", "suspicious", "insufficient_evidence"])
    @pytest.mark.parametrize("action", ["none", "money", "otp_credentials"])
    def test_no_contact_match(self, band, outcome, action):
        res = decide(band, outcome, "no_match", action)
        assert res == "cannot_verify_use_another_route"

    # 3. Confirmed verification with high voice risk -> conflicting signals
    def test_confirmed_with_high_risk_triggers_second_channel(self):
        res = decide("high", "suspicious", "confirmed", "money")
        assert res == "conflicting_signals_use_second_channel"

    # 4. Confirmed verification with low or uncertain voice -> verified normal caution
    @pytest.mark.parametrize("band,outcome", [
        ("low", "likely_genuine"),
        ("medium", "likely_genuine"),
        ("low", "insufficient_evidence"),
        ("insufficient", "insufficient_evidence"),
    ])
    def test_confirmed_with_low_or_uncertain_voice(self, band, outcome):
        res = decide(band, outcome, "confirmed", "money")
        assert res == "verified_normal_caution"

    # 5. High voice risk with unconfirmed verification -> hold_unverified_high_risk
    @pytest.mark.parametrize("verification", ["not_started", "pending", "expired"])
    def test_high_risk_unconfirmed_triggers_hold(self, verification):
        res = decide("high", "suspicious", verification, "money")
        assert res == "hold_unverified_high_risk"

    # 6. Low/uncertain voice with pending or expired verification
    @pytest.mark.parametrize("verification", ["pending", "expired"])
    @pytest.mark.parametrize("action", ["money", "otp_credentials", "confidential"])
    def test_pending_or_expired_sensitive_action_triggers_unverified_hold(self, verification, action):
        res = decide("low", "likely_genuine", verification, action)
        assert res == "unverified_hold"

    @pytest.mark.parametrize("verification", ["pending", "expired"])
    @pytest.mark.parametrize("action", ["none", "other"])
    def test_pending_or_expired_non_sensitive_triggers_caution(self, verification, action):
        res = decide("low", "likely_genuine", verification, action)
        assert res == "unverified_caution"

    # 7. Verification not started with uncertain voice
    @pytest.mark.parametrize("band,outcome", [
        ("medium", "likely_genuine"),
        ("low", "insufficient_evidence"),
        ("insufficient", "insufficient_evidence"),
    ])
    def test_not_started_uncertain_voice(self, band, outcome):
        res = decide(band, outcome, "not_started", "money")
        assert res == "insufficient_evidence_verify_if_sensitive"

    # 8. Verification not started with low voice
    def test_not_started_low_voice_sensitive_action(self):
        res = decide("low", "likely_genuine", "not_started", "money")
        assert res == "no_indicators_verify_before_transfer"

    def test_not_started_low_voice_non_sensitive_action(self):
        res = decide("low", "likely_genuine", "not_started", "none")
        assert res == "no_indicators_not_proof"


class TestVoiceClassHelper:
    def test_insufficient_evidence_forces_uncertain(self):
        assert voice_class("high", "insufficient_evidence") == "uncertain"
        assert voice_class("low", "insufficient_evidence") == "uncertain"
        assert voice_class("medium", "insufficient_evidence") == "uncertain"

    def test_band_mappings(self):
        assert voice_class("high", "suspicious") == "high"
        assert voice_class("medium", "likely_genuine") == "uncertain"
        assert voice_class("low", "likely_genuine") == "low"
