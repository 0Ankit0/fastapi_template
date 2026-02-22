from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from pydantic import field_serializer
from src.apps.core.security import TokenType
from ..utils.hashid import encode_id


class TokenTrackingResponse(SQLModel):
    id: str
    user_id: str
    token_jti: str
    token_type: TokenType
    ip_address: str
    user_agent: str
    is_active: bool
    revoked_at: Optional[datetime]
    revoke_reason: str
    expires_at: datetime
    created_at: datetime

    @field_serializer("id", "user_id")
    def serialize_ids(self, value: int) -> str:
        return encode_id(value)
