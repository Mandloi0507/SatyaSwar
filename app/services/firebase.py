"""
SatyaSwar - Firebase Admin SDK Service
Member 2: Backend, Infrastructure, Database and Security

This module manages the Firebase Admin SDK singleton lifecycle, provides Firestore
client access, and handles secure Firebase ID token verification.
"""

import logging
import os
from typing import Any, Optional

import firebase_admin
from firebase_admin import auth, credentials, firestore

from app.config import get_settings

logger = logging.getLogger(__name__)


def init_firebase() -> Optional[firebase_admin.App]:
    """
    Initialize the Firebase Admin SDK singleton.
    Prevents duplicate initialization if the default app is already initialized.

    Supports:
    - Explicit local service-account JSON key file via `google_application_credentials`.
    - Google Application Default Credentials (ADC) for Cloud Run / GCE deployment.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = get_settings()
    cred = None

    if settings.google_application_credentials:
        cred_path = os.path.abspath(settings.google_application_credentials)
        if os.path.exists(cred_path):
            logger.info("Initializing Firebase Admin with service account certificate: %s", cred_path)
            cred = credentials.Certificate(cred_path)
        else:
            logger.warning(
                "Configured google_application_credentials path does not exist (%s). "
                "Falling back to Application Default Credentials.",
                cred_path,
            )

    if cred is None:
        try:
            logger.info("Initializing Firebase Admin with Application Default Credentials (ADC)")
            cred = credentials.ApplicationDefault()
        except Exception as e:
            logger.error("Failed to acquire Application Default Credentials: %s", e)
            raise RuntimeError(
                "Firebase credentials not found. Provide a valid service account JSON via "
                "GOOGLE_APPLICATION_CREDENTIALS or configure Google Application Default Credentials."
            ) from e

    options: dict[str, Any] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id

    app = firebase_admin.initialize_app(cred, options=options or None)
    logger.info("Firebase Admin SDK successfully initialized (app: %s, project: %s)", app.name, options.get("projectId", "default"))
    return app


def get_firestore_client() -> firestore.Client:
    """
    Returns the Cloud Firestore client instance.
    Initializes Firebase Admin if not already initialized.
    """
    init_firebase()
    return firestore.client()


# Alias recommended by Member 2 build guide
db = get_firestore_client


def verify_id_token(token: str, check_revoked: bool = True) -> dict[str, Any]:
    """
    Verifies a Firebase ID token and returns the decoded token payload.

    Args:
        token: Raw Firebase ID token string.
        check_revoked: When True, checks whether the token has been revoked or
                       the user has been disabled.

    Returns:
        dict containing decoded token claims (e.g. 'uid', 'email', 'name').

    Raises:
        auth.InvalidIdTokenError: Token is malformed or invalid.
        auth.ExpiredIdTokenError: Token has expired.
        auth.RevokedIdTokenError: Token has been revoked.
        auth.UserDisabledError: User account is disabled.
        auth.CertificateFetchError: Failed to fetch public key certificates.
        ValueError: Token string is empty or invalid type.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Invalid token: token must be a non-empty string")

    init_firebase()
    # Note: Tokens are never logged to prevent credential leakage.
    return auth.verify_id_token(token, check_revoked=check_revoked)
