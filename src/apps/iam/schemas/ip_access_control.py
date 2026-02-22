from datetime import datetime
from sqlmodel import SQLModel
from pydantic import field_serializer
from ..models.ip_access_control import IpAccessStatus
from ..utils.hashid import encode_id


class IPAccessControlResponse(SQLModel):
    id: str
    user_id: str
    ip_address: str
    status: IpAccessStatus
    reason: str
    last_seen: datetime
    created_at: datetime

    @field_serializer("id", "user_id")
    def serialize_ids(self, value: int) -> str:
        return encode_id(value)


class IPAccessControlUpdate(SQLModel):
    status: IpAccessStatus
    reason: str = ""
