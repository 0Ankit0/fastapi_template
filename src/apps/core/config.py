from typing import List, Union
from pydantic import AnyHttpUrl, SecretStr, SecretStr, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Template"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    REFRESH_TOKEN_EXPIRE_DAYS:int = 7
    ACCESS_TOKEN_COOKIE: str = "access_token"
    REFRESH_TOKEN_COOKIE: str = "refresh_token"

    SECURE_COOKIES: bool = False
    
    # Account security settings
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    REQUIRE_EMAIL_VERIFICATION: bool = False
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # Debug settings for environment
    DEBUG: bool = True

    # CORS settings
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = ["http://localhost", "http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("Invalid CORS origins format", v)
    
    # PostgreSQL settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "mydatabase"
    DATABASE_URL: str | None = None
    SYNC_DATABASE_URL: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: str | None, info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        debug: bool = data.get("DEBUG") or True 
        if debug:
            return f"sqlite+aiosqlite:///./{data.get('POSTGRES_DB')}.db"
        else:
            return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}/{data.get('POSTGRES_DB')}"
        
    @field_validator("SYNC_DATABASE_URL", mode="before")
    def assemble_sync_db_connection(cls, v: str | None, info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        debug: bool = data.get("DEBUG") or True
        if debug:
            return f"sqlite:///./{data.get('POSTGRES_DB')}.db"
        else:
            return f"postgresql://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}/{data.get('POSTGRES_DB')}"
    
    # Email settings
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: str = "smtp.example.com"
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = "user@example.com"
    EMAIL_HOST_PASSWORD: SecretStr = SecretStr("password")
    EMAIL_FROM_ADDRESS: str = "noreply@example.com"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    SERVER_HOST: str = "http://localhost:8000"

    # Social auth settings
    GOOGLE_CLIENT_ID: str = "your-google-client-id"
    GOOGLE_CLIENT_SECRET: str = "your-google-client-secret"
    FACEBOOK_CLIENT_ID: str = "your-facebook-client-id"
    FACEBOOK_CLIENT_SECRET: str = "your-facebook-client-secret"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()