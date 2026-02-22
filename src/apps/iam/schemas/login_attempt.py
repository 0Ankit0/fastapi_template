from datetime import datetime
from sqlmodel import SQLModel
from pydantic import field_serializer
from ..utils.hashid import encode_id


class LoginAttemptResponse(SQLModel):
    id: str
    user_id: str
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: str
    timestamp: datetime

    @field_serializer("id", "user_id")
    def serialize_ids(self, value: int) -> str:
        return encode_id(value)
