from __future__ import annotations

from dotenv import load_dotenv
import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings,SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )
    
    MEDIA_DIR: str = "media"
    MEDIA_URL: str = "/media"
    STORAGE_BACKEND: str = "local"
    SERVER_HOST: str = "http://localhost:8000"
    MEDIA_BASE_URL: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str = ""
    S3_USE_PATH_STYLE: bool = False
    MAX_AVATAR_SIZE_MB: int = 5

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr("")

    APP_INSTANCE_NAME: str = "fastapi_template"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_TIME_LIMIT: int = 300
    CELERY_RESULT_EXPIRES: int = 3600
    CELERY_QUEUE_DEFAULT: str = "default"
    CELERY_TASK_ALWAYS_EAGER: bool = True

    FRONTEND_URL: str = "http://localhost:3000"

    EMAIL_SERVICE_ENABLED: bool = True
    EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: str = "smtp"
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: SecretStr = SecretStr("")
    EMAIL_FROM_ADDRESS: str = ""

    DEBUG: bool = True
    REDIS_URL: str = ""
    REDIS_MAX_CONNECTIONS: int = 10
    API_KEY: str = ""
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""

    ACCESS_TOKEN_COOKIE_NAME: str = "access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    SECURE_COOKIES: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None

    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_SIGNUP: str = "2/minute"
    RATE_LIMIT_PASSWORD_RESET: str = "3/minute"
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 15

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool  = True
    PASSWORD_REQUIRE_DIGIT: bool    = True

    REQUIRE_EMAIL_VERIFICATION: bool = True

    HASHIDS_SALT: str = ""
    HASHIDS_MIN_LENGTH: int = 8
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_PRE_PING: bool = True
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    PASSWORD_PEPPER: str = ""
    PASETO_SECRET_KEY: str = ""


settings : Settings = Settings()