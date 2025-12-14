from fastapi import WebSocket
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_json(self, websocket: WebSocket, data: dict) -> None:
        """Send JSON data to a specific client."""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, data: dict) -> None:
        """Broadcast JSON data to all connected clients."""
        disconnected = []
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(data)
                except Exception:
                    disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
