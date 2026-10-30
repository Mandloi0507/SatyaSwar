"""
SatyaSwar - Database & API Schemas
Member 2: Backend, Infrastructure, Database and Security

Defines Pydantic models for database documents, repository objects, and API data transfers.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AccountStatus,
    ActionType,
    ContactStatus,
    EvidenceQualityLevel,
    FinalOutcome,
    RiskLevel,
    SessionStatus,
    VerificationStatus,
)


class UserProfile(BaseModel):
    """Firestore 'users' document schema."""

    model_config = ConfigDict(from_attributes=True)

    uid: str = Field(description="Firebase Auth UID")
    name: str = Field(default="", description="Registered display name")
    email: str = Field(default="", description="User email address")
    phone: Optional[str] = Field(default=None, description="Optional contact phone number")
    account_status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="Account lifecycle status")
    created_at: Optional[Any] = Field(default=None, description="Server timestamp of creation")
    updated_at: Optional[Any] = Field(default=None, description="Server timestamp of last update")


class UserUpdate(BaseModel):
    """Payload schema for updating user profile fields."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=80, description="Updated display name")
    phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{7,15}$", description="E.164 phone number format")


class TrustedContact(BaseModel):
    """
    Firestore 'trusted_contacts' document schema.
    Owner-specific record ensuring personal aliases and labels remain private to owner_uid.
    Identity is strictly keyed to contact_uid (Firebase UID).
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(default=None, description="Firestore document ID")
    owner_uid: str = Field(description="UID of the user who owns this contact relationship entry")
    contact_uid: Optional[str] = Field(default=None, description="UID of the linked contact (set on accept)")
    registered_name: str = Field(default="", description="Registered name of the contact from their profile")
    alias: Optional[str] = Field(default=None, description="Owner-specific custom alias (e.g. 'Priti')")
    label: Optional[str] = Field(default=None, description="Disambiguation label for duplicate names (e.g. 'college')")
    status: ContactStatus = Field(default=ContactStatus.PENDING, description="Relationship status")
    invite_code_hash: Optional[str] = Field(default=None, description="SHA256 hash of single-use invite code")
    invite_expires_at: Optional[Any] = Field(default=None, description="Expiration timestamp of invite")
    created_at: Optional[Any] = Field(default=None, description="Server timestamp of creation")
    updated_at: Optional[Any] = Field(default=None, description="Server timestamp of last update")


class CallSession(BaseModel):
    """Firestore 'call_sessions' document schema representing live session state."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="Unique call session identifier")
    user_id: str = Field(description="UID of the session owner")
    status: SessionStatus = Field(default=SessionStatus.CREATED, description="Lifecycle state of the session")
    start_time: Optional[Any] = Field(default=None, description="Timestamp when session became active")
    end_time: Optional[Any] = Field(default=None, description="Timestamp when session ended")
    latest_risk_score: Optional[float] = Field(default=None, description="Current rolling risk score [0.0 - 1.0]")
    risk_level: RiskLevel = Field(default=RiskLevel.UNAVAILABLE, description="Current categorical risk band")
    evidence_quality: EvidenceQualityLevel = Field(default=EvidenceQualityLevel.POOR, description="Latest window evidence quality")
    verification_status: VerificationStatus = Field(default=VerificationStatus.NOT_REQUESTED, description="Current contact verification status")
    window_count: int = Field(default=0, ge=0, description="Number of audio analysis windows processed")
    created_at: Optional[Any] = Field(default=None, description="Server timestamp of creation")
    updated_at: Optional[Any] = Field(default=None, description="Server timestamp of last update")


class VerificationRequest(BaseModel):
    """Firestore 'verification_requests' document schema for independent caller verification."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(default=None, description="Firestore document ID")
    session_id: str = Field(description="Associated call session ID")
    requester_id: str = Field(description="UID of the user requesting verification")
    contact_user_id: str = Field(description="UID of the designated trusted contact")
    claimed_identity: str = Field(description="Identity name claimed during the call")
    action_type: ActionType = Field(default=ActionType.OTHER, description="Type of sensitive action requested")
    amount: Optional[float] = Field(default=None, ge=0.0, description="Optional monetary amount if financial request")
    status: VerificationStatus = Field(default=VerificationStatus.PENDING, description="Current status of the request")
    code_hash: Optional[str] = Field(default=None, description="Cryptographic hash of match code challenge")
    attempts: int = Field(default=0, ge=0, description="Number of verification attempts made")
    max_attempts: int = Field(default=3, ge=1, description="Maximum allowed verification attempts")
    created_at: Optional[Any] = Field(default=None, description="Server timestamp of creation")
    expires_at: Optional[Any] = Field(default=None, description="Expiration timestamp of the request")
    responded_at: Optional[Any] = Field(default=None, description="Timestamp when responder approved/denied")


class CallHistoryItem(BaseModel):
    """
    Firestore 'call_history' document schema.
    Compact, scores-only summary persisted upon session completion.
    NO raw audio or transcripts are ever stored.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(default=None, description="Firestore document ID")
    user_id: str = Field(description="UID of the call owner")
    session_id: str = Field(description="Associated call session ID")
    claimed_contact: str = Field(default="", description="Contact identity evaluated during call")
    risk_score: Optional[float] = Field(default=None, description="Peak or final rolling risk score [0.0 - 1.0]")
    risk_level: RiskLevel = Field(default=RiskLevel.UNAVAILABLE, description="Final categorical risk level")
    evidence_quality: EvidenceQualityLevel = Field(default=EvidenceQualityLevel.POOR, description="Overall evidence quality level")
    verification_status: VerificationStatus = Field(default=VerificationStatus.NOT_REQUESTED, description="Final verification status")
    final_outcome: FinalOutcome = Field(default=FinalOutcome.UNAVAILABLE, description="Server-evaluated final decision outcome")
    created_at: Optional[Any] = Field(default=None, description="Session completion timestamp")
    expires_at: Optional[Any] = Field(default=None, description="TTL timestamp for automated data retention cleanup")


class DeviceToken(BaseModel):
    """Firestore 'device_tokens' document schema for FCM push notifications."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(description="UID of the device owner")
    token: str = Field(description="FCM registration token")
    platform: str = Field(default="android", description="Client device platform (android | ios)")
    updated_at: Optional[Any] = Field(default=None, description="Server timestamp of registration/update")
