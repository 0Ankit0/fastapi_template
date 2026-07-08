from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect

from src.apps.realtime.schemas import Connection, SSEConnection

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, Connection] = {}
        self.sse_connections: dict[str, SSEConnection] = {}
        self.user_connections: dict[int, set[str]] = defaultdict(set)
        self.org_connections: dict[str, set[str]] = defaultdict(set)
        self.user_sse_connections: dict[int, set[str]] = defaultdict(set)
        self.org_sse_connections: dict[str, set[str]] = defaultdict(set)

    async def connect(self, connection: Connection):
        await self.connect_websocket(connection)

    async def connect_websocket(self, connection: Connection):
        self.connections[connection.connection_id] = connection
        self.user_connections[connection.user_id].add(connection.connection_id)
        self.org_connections[connection.organization_slug].add(connection.connection_id)

    async def connect_sse(self, connection: SSEConnection):
        self.sse_connections[connection.connection_id] = connection
        self.user_sse_connections[connection.user_id].add(connection.connection_id)
        self.org_sse_connections[connection.organization_slug].add(connection.connection_id)

    def disconnect(self, connection_id: str):
        connection = self.connections.pop(connection_id, None)
        if connection:
            user_id = connection.user_id
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                self.user_connections.pop(user_id, None)

            org_slug = connection.organization_slug
            self.org_connections[org_slug].discard(connection_id)
            if not self.org_connections[org_slug]:
                self.org_connections.pop(org_slug, None)

        sse_connection = self.sse_connections.pop(connection_id, None)
        if sse_connection:
            user_id = sse_connection.user_id
            self.user_sse_connections[user_id].discard(connection_id)
            if not self.user_sse_connections[user_id]:
                self.user_sse_connections.pop(user_id, None)

            org_slug = sse_connection.organization_slug
            self.org_sse_connections[org_slug].discard(connection_id)
            if not self.org_sse_connections[org_slug]:
                self.org_sse_connections.pop(org_slug, None)

    async def _safe_send(self, connection_id: str, payload: dict) -> bool:
        """Send a WebSocket payload; return True only if delivery succeeded."""
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        try:
            await connection.websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(
                "Failed sending to connection %s, cleaning up: %s",
                connection_id,
                e,
            )
            self.disconnect(connection_id)
            return False

    def _safe_queue_sse(self, connection_id: str, payload: dict) -> bool:
        connection = self.sse_connections.get(connection_id)
        if not connection:
            return False

        try:
            connection.queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            logger.warning("SSE queue full for connection %s, cleaning up", connection_id)
            self.disconnect(connection_id)
            return False

    async def send_to_user(self, user_id: int, payload: dict) -> int:
        delivered = 0

        connection_ids = list(self.user_connections.get(user_id, set()))
        for connection_id in connection_ids:
            if await self._safe_send(connection_id, payload):
                delivered += 1

        for connection_id in list(self.user_sse_connections.get(user_id, set())):
            if self._safe_queue_sse(connection_id, payload):
                delivered += 1

        return delivered

    async def send_to_org(self, org_slug: str, payload: dict) -> int:
        delivered = 0

        connection_ids = list(self.org_connections.get(org_slug, set()))
        for connection_id in connection_ids:
            if await self._safe_send(connection_id, payload):
                delivered += 1

        for connection_id in list(self.org_sse_connections.get(org_slug, set())):
            if self._safe_queue_sse(connection_id, payload):
                delivered += 1

        return delivered

manager = ConnectionManager()