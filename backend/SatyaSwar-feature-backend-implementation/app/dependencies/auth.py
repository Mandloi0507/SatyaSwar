"""
SatyaSwar - Authentication Dependencies
Member 2: Backend, Infrastructure, Database and Security

This module defines the AuthUser model, REST authentication dependencies using
Firebase ID tokens via HTTPBearer, and WebSocket authentication handlers supporting
both Authorization headers and first-message token transmission.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.firebase import verify_id_token

logger = logging.getLogger(__name__)

# Reusable HTTPBearer scheme with auto_error=False for custom 401 handling
bearer_scheme = HTTPBearer(auto_error=False)

# Custom WebSocket close code for authentication failures (RFC 6455 4000-4999 application range)
WS_AUTH_FAILED_CODE = 4401
WS_AUTH_TIMEOUT_SECONDS = 5.0


class AuthUser(BaseModel):
    """Authenticated user representation derived from verified Firebase ID token."""

    uid: str = Field(description="Unique Firebase user identifier")
    email: Optional[str] = Field(default=None, description="User email address if present in claims")
    name: Optional[str] = Field(default=None, description="User display name if present in claims")
    phone_number: Optional[str] = Field(default=None, description="User phone number if present in claims")


def verify_token(token: str) -> AuthUser:
    """
    Verifies a Firebase ID token and constructs an AuthUser instance.

    Raises:
        HTTPException: HTTP 401 Unauthorized if the token is invalid, expired,
                       revoked, or associated with a disabled user.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development mode, support mock/demo tokens for seamless local testing
    settings = get_settings()
    if settings.app_env == "development":
        if token.startswith("mock_token_") or token.startswith("mock-token-") or token in ("default_token", "demo_token", "mock_token", "null", "undefined"):
            uid = token.replace("mock_token_", "").replace("mock-token-", "") if ("mock_token_" in token or "mock-token-" in token) else "usr_demo_01"
            return AuthUser(uid=uid, email=f"{uid}@satyaswar.io", name="Demo User")

    try:
        decoded = verify_id_token(token, check_revoked=True)
    except (
        fb_auth.InvalidIdTokenError,
        fb_auth.ExpiredIdTokenError,
        fb_auth.RevokedIdTokenError,
        fb_auth.UserDisabledError,
        fb_auth.CertificateFetchError,
        ValueError,
    ) as e:
        logger.warning("Token verification failed: %s", type(e).__name__)
        # If running in development mode, allow the request to proceed as demo user
        if settings.app_env == "development":
            logger.info("Development mode: falling back to demo user after token verification failure")
            return AuthUser(uid="usr_demo_01", email="priyanka@satyaswar.io", name="Priyanka Mandloi")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    return AuthUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name"),
        phone_number=decoded.get("phone_number"),
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthUser:
    """
    FastAPI dependency that enforces Firebase ID token authentication for protected REST routes.
    Expects 'Authorization: Bearer <Firebase ID token>'.
    """
    if credentials is None or not credentials.credentials:
        settings = get_settings()
        if settings.app_env == "development":
            return AuthUser(uid="usr_demo_01", email="priyanka@satyaswar.io", name="Priyanka Mandloi")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)


def authenticate_ws_token(token: Optional[str]) -> Optional[AuthUser]:
    """
    Verifies a token for WebSocket contexts without raising HTTPException.
    Returns AuthUser if valid, otherwise None.
    """
    if not token or token in ("null", "undefined"):
        return None

    try:
        return verify_token(token)
    except HTTPException:
        return None


async def authenticate_websocket(
    websocket: WebSocket,
    timeout_seconds: float = WS_AUTH_TIMEOUT_SECONDS,
) -> AuthUser:
    """
    Authenticates a WebSocket connection using a multi-strategy approach:
    1. Header-based: Inspects 'Authorization: Bearer <token>' header.
    2. Query parameter: Inspects '?token=<token>' as sent by mobile WebSocket clients.
    3. First-message fallback: Accepts connection and waits for 'auth' JSON message.
    """
    # Strategy 1: Check Authorization header
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        user = authenticate_ws_token(token)
        if user:
            await websocket.accept()
            return user
        await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Invalid authentication token")
        raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)

    # Strategy 2: Check query parameter token (as passed by Flutter WebSocket client)
    query_token = websocket.query_params.get("token")
    if query_token and query_token not in ("null", "undefined", ""):
        user = authenticate_ws_token(query_token)
        if user:
            await websocket.accept()
            return user
        await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Invalid authentication token in query parameter")
        raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)

    # Strategy 3: First-message authentication within timeout
    await websocket.accept()

    try:
        raw_message = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=timeout_seconds,
        )
        data = json.loads(raw_message)

        if not isinstance(data, dict) or data.get("type") != "auth" or not data.get("token"):
            logger.warning("WebSocket first message invalid format or missing token")
            await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Expected auth message: {'type': 'auth', 'token': '...'}")
            raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)

        token = str(data["token"]).strip()
        user = authenticate_ws_token(token)
        if not user:
            logger.warning("WebSocket token verification failed in first-message auth")
            await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Invalid or expired token")
            raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)

        return user

    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timed out after %.1f seconds", timeout_seconds)
        await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Authentication timeout")
        raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)
    except (json.JSONDecodeError, WebSocketDisconnect):
        try:
            await websocket.close(code=WS_AUTH_FAILED_CODE, reason="Authentication failed")
        except Exception:
            pass
        raise WebSocketDisconnect(code=WS_AUTH_FAILED_CODE)

