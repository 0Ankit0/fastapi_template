from datetime import datetime, timedelta, timezone
from typing import Any, Union
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.apps.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_password_reset_token(subject: Union[str, Any]) -> str:
    """Create a password reset token valid for 1 hour"""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "password_reset"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_email_verification_token(subject: Union[str, Any]) -> str:
    """Create an email verification token valid for 24 hours"""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "email_verification"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_temp_auth_token(subject: Union[str, Any]) -> str:
    """Create a temporary auth token for OTP validation, valid for 5 minutes"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "temp_auth"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str | None = None) -> dict:
    """
    Decode and verify a JWT token.
    If token_type is provided, checks that the 'type' claim matches.
    Raises jwt.JWTError if the token is invalid, expired, or has wrong type.
    Returns the payload dictionary on success.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if token_type and payload.get("type") != token_type:
        raise JWTError(f"Invalid token type, expected {token_type}")
    return payload

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)