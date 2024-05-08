from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """read the settings from .env file"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    # telegram
    tg_api_id: int
    tg_api_hash: str
    tg_bot_token: str
    tg_group_topic_id: int

    # whatsapp
    wa_phone_id: int
    wa_business_id: int
    wa_verify_token: str
    wa_token: str
    wa_phone_number: int
    wa_app_id: int
    wa_app_secret: str
    wa_callback_url: str
    wa_webhook_endpoint: str

    port: int
    httpx_timeout: float
    debug: bool


@lru_cache
def get_settings() -> Settings:
    """get the settings from .env file"""
    return Settings()
