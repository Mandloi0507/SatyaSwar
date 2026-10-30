"""
SatyaSwar - WebSocket Connection Manager
Member 2: Backend, Infrastructure, Database and Security

Tracks active WebSocket connections per session ID and broadcasts real-time
risk updates, verification events, and status changes with session-level isolation.
"""

from collections import defaultdict
import logging
from typing import Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSockets grouped by session ID.
    Enforces per-session boundaries: messages broadcast for session A
    are never transmitted to sockets connected to session B.
    """

    def __init__(self):
        self._by_session: dict[str, set[WebSocket]] = defaultdict(set)

    def add(self, session_id: str, websocket: WebSocket) -> None:
        """Register an authenticated WebSocket for a session."""
        self._by_session[session_id].add(websocket)
        logger.info(
            "WebSocket connected for session %s (active connections: %d)",
            session_id,
            len(self._by_session[session_id]),
        )

    def remove(self, session_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection upon disconnect or error."""
        if session_id in self._by_session:
            self._by_session[session_id].discard(websocket)
            if not self._by_session[session_id]:
                self._by_session.pop(session_id, None)
            logger.info("WebSocket removed for session %s", session_id)

    def active_count(self, session_id: str) -> int:
        """Returns the number of active sockets connected for a given session."""
        return len(self._by_session.get(session_id, set()))

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        """
        Broadcasts a JSON-serializable dictionary to all active sockets for a session.
        Stale or dead connections are safely pruned during broadcasting.
        """
        connections = list(self._by_session.get(session_id, set()))
        if not connections:
            return

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to deliver message to WebSocket in session %s: %s",
                    session_id,
                    e,
                )
                self.remove(session_id, ws)

    async def close_session(self, session_id: str, code: int = 1000, reason: str = "") -> None:
        """Closes all active sockets for a given session."""
        connections = list(self._by_session.get(session_id, set()))
        for ws in connections:
            try:
                await ws.close(code=code, reason=reason)
            except Exception:
                pass
            self.remove(session_id, ws)


# Global singleton connection manager
manager = ConnectionManager()
