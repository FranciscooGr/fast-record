"""
WebSocket Connection Manager — handles active dashboard connections.

Provides a singleton `manager` that backend services can import to
broadcast real-time update signals to connected frontend clients.

Usage in services:
    from app.api.v1.websockets import manager
    await manager.broadcast(usuario_id, "update_dashboard")
"""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections keyed by usuario_id."""

    def __init__(self) -> None:
        # usuario_id → list of active WebSocket connections
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, usuario_id: int, websocket: WebSocket) -> None:
        """Accept the WebSocket and register it under the given user."""
        await websocket.accept()
        self._connections.setdefault(usuario_id, []).append(websocket)
        logger.info("WS connected: usuario_id=%d  (total=%d)", usuario_id, len(self._connections[usuario_id]))

    def disconnect(self, usuario_id: int, websocket: WebSocket) -> None:
        """Remove a WebSocket from the registry."""
        conns = self._connections.get(usuario_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(usuario_id, None)
        logger.info("WS disconnected: usuario_id=%d", usuario_id)

    async def broadcast(self, usuario_id: int, message: str) -> None:
        """Send a text message to every connection for the given user."""
        conns = self._connections.get(usuario_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        # Clean up broken connections
        for ws in dead:
            self.disconnect(usuario_id, ws)
        if conns:
            logger.info("WS broadcast to usuario_id=%d: '%s' (%d clients)", usuario_id, message, len(conns))


# ── Singleton instance used across the app ──────────────────────
manager = ConnectionManager()
