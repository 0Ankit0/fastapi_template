from datetime import datetime
from typing import Optional
from src.core.schemas import BaseSchema
from src.core.types import HashId
from src.core.security import TokenType


class TokenTrackingResponse(BaseSchema):
    id: HashId
    user_id: HashId
    token_jti: str
    token_type: TokenType
    ip_address: str
    user_agent: str
    revoked_at: Optional[datetime]
    revoke_reason: str
    expires_at: datetime
    created_at: datetime


