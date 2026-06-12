from typing import Optional
from src.core.schemas import BaseSchema

class Token(BaseSchema):
    access: str
    refresh: str
    token_type: str = "bearer"

class TokenPayload(BaseSchema):
    sub: Optional[str] = None
    refresh: Optional[bool] = False

