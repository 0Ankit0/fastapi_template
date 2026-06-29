import logging
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect

from src.apps.websockets.schemas import Connection

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, Connection] = {}
        self.user_connections: dict[int, set[str]] = defaultdict(set)
        self.org_connections: dict[str, set[str]] = defaultdict(set)

    async def connect(self, connection: Connection):
        self.connections[connection.connection_id] = connection
        self.user_connections[connection.user_id].add(connection.connection_id)
        self.org_connections[connection.organization_slug].add(connection.connection_id)

    def disconnect(self, connection_id: str):
        connection = self.connections.pop(connection_id, None)
        if not connection:
            return

        # Clean up user connections and prevent memory leaks
        user_id = connection.user_id
        self.user_connections[user_id].discard(connection_id)
        if not self.user_connections[user_id]:
            self.user_connections.pop(user_id, None)

        # Clean up organization connections
        org_slug = connection.organization_slug
        self.org_connections[org_slug].discard(connection_id)
        if not self.org_connections[org_slug]:
            self.org_connections.pop(org_slug, None)

    async def _safe_send(self, connection_id: str, payload: dict):
        """Helper to send data safely and clean up if the socket is dead."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        try:
            await connection.websocket.send_json(payload)
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(f"Failed sending to connection {connection_id}, cleaning up: {e}")
            self.disconnect(connection_id)

    async def send_to_user(self, user_id: int, payload: dict):
        # Cast to list to prevent "RuntimeError: dictionary changed size during iteration"
        connection_ids = list(self.user_connections.get(user_id, set()))
        for connection_id in connection_ids:
            await self._safe_send(connection_id, payload)

    async def send_to_org(self, org_slug: str, payload: dict):
        connection_ids = list(self.org_connections.get(org_slug, set()))
        for connection_id in connection_ids:
            await self._safe_send(connection_id, payload)

manager = ConnectionManager()