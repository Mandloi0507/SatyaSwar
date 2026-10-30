"""
SatyaSwar - Database & API Schemas
Member 2: Backend, Infrastructure, Database and Security

Defines Pydantic models for database documents, repository objects, and API data transfers.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

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

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamps(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "__class__") and "Sentinel" in v.__class__.__name__:
            return datetime.now(timezone.utc).isoformat()
        return str(v)


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

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamps(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "__class__") and "Sentinel" in v.__class__.__name__:
            return datetime.now(timezone.utc).isoformat()
        return str(v)


class InviteCreateRequest(BaseModel):
    """Payload to generate a new trusted-contact invite."""

    invitee_email: Optional[str] = Field(default=None, description="Optional target email address")


class InviteCreateResponse(BaseModel):
    """Response containing single-use invite code, expiration, and QR code payload."""

    code: str = Field(description="Single-use random invitation code (e.g. 'K7M2-9QX4')")
    expires_at: datetime = Field(description="ISO 8601 UTC expiration timestamp")
    qr_payload: str = Field(description="Standardized QR code content: satyaswar:invite:<code>")


class InviteAcceptRequest(BaseModel):
    """Payload to accept an invitation code."""

    code: str = Field(min_length=4, max_length=32, description="Invitation code received from contact")
    alias: Optional[str] = Field(default=None, max_length=50, description="Owner-specific personal alias")
    label: Optional[str] = Field(default=None, max_length=50, description="Disambiguation label for duplicate names")


class ContactUpdateRequest(BaseModel):
    """Payload to update custom alias or label for an existing contact."""

    alias: Optional[str] = Field(default=None, max_length=50, description="Updated personal alias")
    label: Optional[str] = Field(default=None, max_length=50, description="Updated disambiguation label")


class CallCreateRequest(BaseModel):
    """Payload to initialize a new call analysis session."""

    scenario_id: Optional[str] = Field(default=None, description="Preset test scenario identifier")
    claimed_name: Optional[str] = Field(default=None, description="Name claimed by the caller")
    caller_number: Optional[str] = Field(default="Unknown", description="Caller phone number or identifier")
    direction: Optional[str] = Field(default="incoming", description="Call direction (incoming | outgoing)")


class CallCreateResponse(BaseModel):
    """Response containing created session ID and WebSocket connection endpoint."""

    session_id: str = Field(description="Unique session ID")
    status: SessionStatus = Field(description="Initial session status (CREATED)")
    ws_url: str = Field(description="WebSocket endpoint URL for audio streaming")
    config: dict[str, Any] = Field(description="Agreed audio slicing and window parameters")
    server_time: datetime = Field(description="Server timestamp in UTC")


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

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamps(self, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "__class__") and "Sentinel" in v.__class__.__name__:
            return datetime.now(timezone.utc).isoformat()
        return str(v)


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

