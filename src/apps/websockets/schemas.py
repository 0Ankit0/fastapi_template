from dataclasses import dataclass
from fastapi import WebSocket


@dataclass
class Connection:
    connection_id: str
    user_id: int
    organization_slug: str
    websocket: WebSocket