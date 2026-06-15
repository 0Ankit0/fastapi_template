from typing import Optional
from src.core.schemas import BaseSchema

class Token(BaseSchema):
    access: str
    refresh: str
    token_type: str = "bearer"

class TokenPayload(BaseSchema):
    exp: str
    org: str
    sub: str
    type: str
    jti: str
    refresh: bool | None = None

