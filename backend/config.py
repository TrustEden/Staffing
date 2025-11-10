from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/healthcare_staffing"
    )
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24
    default_tiered_release_hours: int = 24
    otp_enabled: bool = False
    redis_url: str = "redis://localhost:6379"

    # External Notification Settings (optional)
    sendgrid_api_key: str | None = None
    sendgrid_from_email: str = "noreply@healthcarebridge.com"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
