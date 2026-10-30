"""
SatyaSwar - System Enums
Member 2: Backend, Infrastructure, Database and Security

Defines standardized string enums across the database, REST APIs, WebSockets,
and decision engines.
"""

from enum import StrEnum


class AccountStatus(StrEnum):
    ACTIVE = "active"
    PENDING_DELETION = "pending_deletion"
    DELETED = "deleted"


class ContactStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REMOVED = "removed"


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNAVAILABLE = "UNAVAILABLE"


class VerificationStatus(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    NO_CONTACT_MATCH = "NO_CONTACT_MATCH"


class EvidenceQualityLevel(StrEnum):
    GOOD = "good"
    LIMITED = "limited"
    POOR = "poor"


class FinalOutcome(StrEnum):
    LIKELY_GENUINE = "likely_genuine"
    LIKELY_IMPERSONATION = "likely_impersonation"
    SUSPICIOUS = "suspicious"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_SIGNALS = "conflicting_signals"
    UNAVAILABLE = "unavailable"


class ActionType(StrEnum):
    MONEY_TRANSFER = "money_transfer"
    OTP_CREDENTIALS = "otp_credentials"
    CONFIDENTIAL_INFO = "confidential_info"
    OTHER = "other"

