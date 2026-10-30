"""
SatyaSwar - Authentication Routes
Member 2: Backend, Infrastructure, Database and Security

This module provides authenticated endpoints to verify token verification for both
REST (via get_current_user) and WebSockets (via authenticate_websocket).
"""

from fastapi import APIRouter, Depends, WebSocket

from app.dependencies.auth import AuthUser, authenticate_websocket, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.get("/me-check")
async def me_check(user: AuthUser = Depends(get_current_user)) -> dict[str, str | None]:
    """
    Verifies that the provided Firebase ID token is valid and returns authenticated claims.
    Requires 'Authorization: Bearer <Firebase ID token>'.
    """
    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
    }


@router.websocket("/ws-test")
async def ws_auth_test(websocket: WebSocket) -> None:
    """
    Test WebSocket endpoint to verify the authentication handshake.
    Supports either:
    1. 'Authorization: Bearer <Firebase ID token>' header on connection.
    2. First-message JSON: '{"type": "auth", "token": "<Firebase ID token>"}' within 5 seconds.
    """
    user = await authenticate_websocket(websocket)
    await websocket.send_json({
        "type": "auth_success",
        "uid": user.uid,
        "email": user.email,
    })
    await websocket.close(code=1000, reason="Authentication test completed successfully")
