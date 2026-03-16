import strawberry
from typing import Optional

@strawberry.type
class AuthPayload:
    access: str
    refresh: str
    token_type: str
    requires_otp: bool = False
    temp_token: Optional[str] = None

@strawberry.input
class SignupInput:
    username: str
    email: str
    password: str
    confirm_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
