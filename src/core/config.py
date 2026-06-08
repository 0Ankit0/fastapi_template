from __future__ import annotations

from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings,SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )
     
    API_KEY: str = ""
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    DEBUG_MODE: bool = True

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool  = True
    PASSWORD_REQUIRE_DIGIT: bool    = True

    HASHIDS_SALT: str = ""
    HASHIDS_MIN_LENGTH: int = 8
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    PASSWORD_PEPPER: str = ""
    PASETO_SECRET_KEY: str = ""


settings : Settings = Settings()