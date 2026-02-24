from datetime import datetime
from pydantic import BaseModel, field_serializer
from ..models.ip_access_control import IpAccessStatus
from ..utils.hashid import encode_id


class IPAccessControlResponse(BaseModel):
    id: int
    user_id: int
    ip_address: str
    status: IpAccessStatus
    reason: str
    last_seen: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "user_id")
    def serialize_ids(self, value: int) -> str:
        return encode_id(value)


class IPAccessControlUpdate(BaseModel):
    status: IpAccessStatus
    reason: str = ""

