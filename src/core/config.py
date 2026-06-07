from __future__ import annotations

from dotenv import load_dotenv
import os

from pydantic_settings import SettingsConfigDict

load_dotenv()

class Settings:

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )
     
    API_KEY: str
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG_MODE: bool

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    PASSWORD_MIN_LENGTH: int
    PASSWORD_REQUIRE_UPPERCASE: bool
    PASSWORD_REQUIRE_LOWERCASE: bool
    PASSWORD_REQUIRE_SPECIAL: bool
    PASSWORD_REQUIRE_DIGIT: bool

    HASHIDS_SALT: str
    HASHIDS_MIN_LENGTH: int
    SQL_ECHO: bool
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT: int
    DB_POOL_RECYCLE: int
    PASSWORD_PEPPER: str
    PASETO_SECRET_KEY: str


settings = Settings()