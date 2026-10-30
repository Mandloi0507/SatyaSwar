"""
Challenge-Response Verification Workflow & State Machine
Authoritative sources:
- SatyaSwar Complete Solution Document.md, Section 9.4 & 8.3
- Implementation.md, Appendix D
- Master Prompt: Critical Requirement 3 (Verification for Sensitive Actions)

Voice analysis is a risk signal, never definitive identity proof.
For sensitive actions (money, OTP/credentials, confidential data),
this workflow coordinates out-of-band verification with the central decision function.
"""

from __future__ import annotations

import random
import time
from typing import Literal

from pydantic import BaseModel

from satyaswar_ml.decision.decide import decide
from satyaswar_ml.schemas import ActionType, BandType, OutcomeType, VerificationStateType


class VerificationRequest(BaseModel):
    request_id: str
    requester_uid: str
    target_uid: str
    claimed_name: str
    action_type: ActionType
    amount: float | None = None
    match_code: str
    challenge_question: str
    status: VerificationStateType = "pending"
    created_at: float
    expires_at: float
    responded_at: float | None = None
    responder_uid: str | None = None
    secondary_channel_recommended: bool = False


class VerificationManager:
    """
    Coordinates verification requests, challenge generation, timeout enforcement,
    and decision-function integration.
    """

    def __init__(self, default_timeout_s: float = 90.0):
        self.default_timeout_s = default_timeout_s
        self.requests: dict[str, VerificationRequest] = {}

    def create_verification_request(
        self,
        requester_uid: str,
        target_uid: str | None,
        claimed_name: str,
        action_type: ActionType,
        amount: float | None = None,
        timeout_s: float | None = None,
    ) -> VerificationRequest:
        """
        Create a new verification request for an ongoing call.
        If target_uid is missing (unlinked contact), request immediately transitions to 'no_match'.
        """
        now = time.time()
        ttl = timeout_s if timeout_s is not None else self.default_timeout_s
        req_id = f"vr_{int(now * 1000)}_{random.randint(1000, 9999)}"

        if not target_uid:
            req = VerificationRequest(
                request_id=req_id,
                requester_uid=requester_uid,
                target_uid="",
                claimed_name=claimed_name,
                action_type=action_type,
                amount=amount,
                match_code="--",
                challenge_question="Contact not linked in SatyaSwar. Cannot verify via independent push.",
                status="no_match",
                created_at=now,
                expires_at=now,
                secondary_channel_recommended=True,
            )
            self.requests[req_id] = req
            return req

        # Generate fresh, unpredictable 2-digit match code (e.g. 10 - 99)
        match_code = f"{random.randint(10, 99)}"

        # Construct specific challenge question (Section 9.4)
        if action_type == "money" and amount:
            challenge = f"Are you on a call with {requester_uid} right now, asking for ₹{amount:,.2f}?"
        elif action_type == "otp_credentials":
            challenge = f"Are you on a call with {requester_uid} right now, requesting an OTP or security code?"
        elif action_type == "confidential":
            challenge = f"Are you on a call with {requester_uid} right now, asking for confidential records?"
        else:
            challenge = f"Are you on a call with {requester_uid} right now?"

        req = VerificationRequest(
            request_id=req_id,
            requester_uid=requester_uid,
            target_uid=target_uid,
            claimed_name=claimed_name,
            action_type=action_type,
            amount=amount,
            match_code=match_code,
            challenge_question=challenge,
            status="pending",
            created_at=now,
            expires_at=now + ttl,
            secondary_channel_recommended=False,
        )
        self.requests[req_id] = req
        return req

    def respond(
        self,
        request_id: str,
        responder_uid: str,
        decision: Literal["confirmed", "denied"],
        entered_match_code: str | None = None,
    ) -> VerificationRequest:
        """
        Record responder's confirmation or denial.
        Must be the authorized target UID and within TTL.
        """
        req = self.requests.get(request_id)
        if not req:
            raise KeyError(f"Verification request {request_id} not found")

        now = time.time()
        # Enforce expiration
        if req.status == "pending" and now > req.expires_at:
            req.status = "expired"
            req.secondary_channel_recommended = True
            return req

        if req.status != "pending":
            raise ValueError(f"Cannot respond to request with status '{req.status}'")

        # Verify identity matches target
        if responder_uid != req.target_uid:
            raise PermissionError("Responder UID does not match registered target UID")

        # If confirming, require correct match code to prevent accidental click-through
        if decision == "confirmed":
            if entered_match_code is not None and entered_match_code != req.match_code:
                # Wrong code entered -> reject confirmation
                raise ValueError("Entered match code does not match challenge")
            req.status = "confirmed"
        else:
            # Explicit denial is absolute override
            req.status = "denied"
            req.secondary_channel_recommended = True

        req.responded_at = now
        req.responder_uid = responder_uid
        return req

    def get_status(self, request_id: str) -> VerificationStateType:
        """
        Retrieve request status with automatic expiry evaluation.
        """
        req = self.requests.get(request_id)
        if not req:
            return "not_started"

        if req.status == "pending" and time.time() > req.expires_at:
            req.status = "expired"
            req.secondary_channel_recommended = True

        return req.status

    def evaluate_decision(
        self,
        request_id: str | None,
        voice_band: BandType,
        voice_outcome: OutcomeType,
        action_type: ActionType,
    ) -> tuple[str, str, bool]:
        """
        Execute central decision function combining voice result and verification state.
        Returns:
        - decision_code: machine readable outcome from decide()
        - recommendation: human guidance for app/dashboard display
        - secondary_channel_required: whether out-of-band phone callback is advised
        """
        verif_state: VerificationStateType = "not_started"
        if request_id:
            verif_state = self.get_status(request_id)

        decision_code = decide(
            voice_band=voice_band,
            voice_outcome=voice_outcome,
            verification=verif_state,
            action_type=action_type,
        )

        # Build recommendation based on decision code
        secondary_channel_required = False
        if decision_code == "likely_impersonation":
            rec = "CRITICAL: Verification was explicitly denied by the claimed contact. DO NOT PROCEED."
            secondary_channel_required = True
        elif decision_code == "cannot_verify_use_another_route":
            rec = "Contact is not linked in SatyaSwar. Call back on a known, pre-saved phone number before sharing sensitive items."
            secondary_channel_required = True
        elif decision_code == "conflicting_signals_use_second_channel":
            rec = "WARNING: Voice analysis flagged high synthetic risk despite push confirmation. Use a separate trusted channel before sensitive action."
            secondary_channel_required = True
        elif decision_code == "verified_normal_caution":
            rec = "Verified via linked account. Proceed with normal caution."
        elif decision_code == "hold_unverified_high_risk":
            rec = "HIGH RISK: Voice indicators show synthetic speech and verification is unconfirmed. Hold action immediately."
            secondary_channel_required = True
        elif decision_code == "unverified_hold":
            rec = "Action held: Verification is incomplete/expired for a sensitive request. Do not send funds or OTP."
            secondary_channel_required = True
        elif decision_code == "unverified_caution":
            rec = "Verification is pending or expired. Exercise caution."
        elif decision_code == "insufficient_evidence_verify_if_sensitive":
            rec = "Audio evidence is insufficient to verify voice authenticity. Verify caller before any sensitive transfer."
        elif decision_code == "no_indicators_verify_before_transfer":
            rec = "Low synthetic indicators detected, but voice alone does not prove identity. Complete verification before funds transfer."
        else:
            rec = "No synthetic indicators detected. Standard caution advised."

        return decision_code, rec, secondary_channel_required
