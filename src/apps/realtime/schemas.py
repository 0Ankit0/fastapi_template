from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from src.core.schemas import BaseSchema


@dataclass(slots=True)
class Connection:
    connection_id: str
    user_id: int
    organization_slug: str
    websocket: WebSocket


@dataclass(slots=True)
class SSEConnection:
    connection_id: str
    user_id: int
    organization_slug: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)


class RealtimeEvent(BaseSchema):
    event: str
    data: dict[str, Any]
    id: str | None = None
    retry: int | None = None