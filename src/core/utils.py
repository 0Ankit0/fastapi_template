from datetime import datetime
from typing import TypedDict
import base64
import json


class CursorData(TypedDict):
    id: str
    created_at: str | None


def encode_cursor(
    row_id: int | str,
    created_at: datetime | None = None,
) -> str:
    payload: CursorData = {
        "id": str(row_id),
        "created_at": (
            created_at.isoformat()
            if created_at is not None
            else None
        ),
    }

    return base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()


def decode_cursor(
    cursor: str,
) -> tuple[datetime | None, str]:
    payload: CursorData = json.loads(
        base64.urlsafe_b64decode(cursor.encode()).decode()
    )

    return (
        datetime.fromisoformat(payload["created_at"])
        if payload["created_at"]
        else None,
        payload["id"],
    )