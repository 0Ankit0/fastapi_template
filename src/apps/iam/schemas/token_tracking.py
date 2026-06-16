from datetime import datetime
from typing import Optional
from pydantic import  computed_field
from src.core.schemas import BaseSchema
from src.core.eums import UserStatus
from src.core.types import HashId
from src.core.security import TokenType


class TokenTrackingResponse(BaseSchema):
    id: HashId
    user_id: HashId
    token_jti: str
    token_type: TokenType
    ip_address: str
    user_agent: str
    status: UserStatus
    revoked_at: Optional[datetime]
    revoke_reason: str
    expires_at: datetime
    created_at: datetime

    @computed_field
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

