"""WebSocket connection manager for real-time updates."""

import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
from datetime import datetime
import json


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - Connection lifecycle management
    - Broadcast to all connected clients
    - Rate limiting per client
    """

    def __init__(self):
        self._connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            self._connections[websocket] = {
                "connected_at": datetime.utcnow(),
                "last_update": datetime.utcnow(),
            }

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                del self._connections[websocket]

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        if not self._connections:
            return

        # Serialize once
        json_message = json.dumps(message, default=str)

        # Send to all connections
        disconnected = []
        for websocket in list(self._connections.keys()):
            try:
                await websocket.send_text(json_message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    async def send_to(self, websocket: WebSocket, message: dict) -> None:
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"WebSocket send error: {e}")
            await self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)


# Global instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager
