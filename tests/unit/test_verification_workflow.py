"""
Unit tests for SatyaSwar Challenge-Response Verification Workflow.
Authoritative source: Master Prompt Critical Requirement 3 & Solution Document Section 9.4.
"""

import time

import pytest

from satyaswar_ml.decision.verification import VerificationManager


def test_create_verification_request_linked_contact():
    vm = VerificationManager(default_timeout_s=60.0)
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid="user_priyanka",
        claimed_name="Priyanka",
        action_type="money",
        amount=50000.0,
    )

    assert req.request_id.startswith("vr_")
    assert req.status == "pending"
    assert len(req.match_code) == 2
    assert "₹50,000.00" in req.challenge_question
    assert req.expires_at > req.created_at


def test_create_verification_request_unlinked_contact():
    vm = VerificationManager()
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid=None,
        claimed_name="Unknown Caller",
        action_type="money",
    )

    assert req.status == "no_match"
    assert req.secondary_channel_recommended is True

    code, rec, sec = vm.evaluate_decision(req.request_id, "low", "likely_genuine", "money")
    assert code == "cannot_verify_use_another_route"
    assert sec is True


def test_verification_denial_overrides_everything():
    vm = VerificationManager()
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid="user_priyanka",
        claimed_name="Priyanka",
        action_type="money",
    )

    # Responder denies
    updated = vm.respond(req.request_id, "user_priyanka", "denied")
    assert updated.status == "denied"

    # Even with low voice score, denial means likely_impersonation
    code, rec, sec = vm.evaluate_decision(req.request_id, "low", "likely_genuine", "money")
    assert code == "likely_impersonation"
    assert "DO NOT PROCEED" in rec
    assert sec is True


def test_verification_confirmation_flow():
    vm = VerificationManager()
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid="user_priyanka",
        claimed_name="Priyanka",
        action_type="money",
        amount=50000.0,
    )

    # Wrong responder UID fails
    with pytest.raises(PermissionError):
        vm.respond(req.request_id, "attacker_uid", "confirmed", entered_match_code=req.match_code)

    # Wrong match code fails
    with pytest.raises(ValueError, match="match code"):
        vm.respond(req.request_id, "user_priyanka", "confirmed", entered_match_code="9999")

    # Correct confirmation
    confirmed = vm.respond(req.request_id, "user_priyanka", "confirmed", entered_match_code=req.match_code)
    assert confirmed.status == "confirmed"

    # Low voice + confirmed -> normal caution
    code, rec, sec = vm.evaluate_decision(req.request_id, "low", "likely_genuine", "money")
    assert code == "verified_normal_caution"
    assert sec is False


def test_conflicting_signals_high_risk_and_confirmed():
    vm = VerificationManager()
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid="user_priyanka",
        claimed_name="Priyanka",
        action_type="money",
    )
    vm.respond(req.request_id, "user_priyanka", "confirmed", req.match_code)

    # High voice risk + confirmed verification -> conflicting signals!
    code, rec, sec = vm.evaluate_decision(req.request_id, "high", "suspicious", "money")
    assert code == "conflicting_signals_use_second_channel"
    assert sec is True


def test_verification_expiration():
    vm = VerificationManager(default_timeout_s=0.01)
    req = vm.create_verification_request(
        requester_uid="user_abhishek",
        target_uid="user_priyanka",
        claimed_name="Priyanka",
        action_type="money",
        timeout_s=0.01,
    )

    time.sleep(0.05)
    # Check status should automatically detect expiry
    assert vm.get_status(req.request_id) == "expired"

    # Responding to an already expired request raises ValueError
    with pytest.raises(ValueError, match="expired"):
        vm.respond(req.request_id, "user_priyanka", "confirmed", req.match_code)

    # Expired + sensitive action -> unverified_hold
    code, rec, sec = vm.evaluate_decision(req.request_id, "low", "likely_genuine", "money")
    assert code == "unverified_hold"
    assert sec is True


def test_low_voice_score_never_independently_authorizes():
    vm = VerificationManager()
    # No verification started yet
    code, rec, sec = vm.evaluate_decision(None, "low", "likely_genuine", "money")
    assert code == "no_indicators_verify_before_transfer"
    assert "does not prove identity" in rec

