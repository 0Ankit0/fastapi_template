from typing import Optional
import strawberry
from src.apps.iam.models.token_tracking import TokenTracking

@strawberry.type
class TokenTrackingType:
    id: int
    user_id: int
    token_jti: str
    token_type: str
    ip_address: str
    user_agent: str
    is_active: bool
    revoked_at: Optional[str]
    revoke_reason: Optional[str]
    expires_at: str
    created_at: str

    @staticmethod
    def from_orm(token: TokenTracking) -> "TokenTrackingType":
        return TokenTrackingType(
            id=token.id,
            user_id=token.user_id,
            token_jti=token.token_jti,
            token_type=token.token_type,
            ip_address=token.ip_address,
            user_agent=token.user_agent,
            is_active=token.is_active,
            revoked_at=str(token.revoked_at) if token.revoked_at else None,
            revoke_reason=token.revoke_reason,
            expires_at=str(token.expires_at),
            created_at=str(token.created_at),
        )
