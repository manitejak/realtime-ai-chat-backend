from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Real-Time AI Chat Backend'
    app_env: str = 'development'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    log_level: str = 'INFO'
    cors_origins: list[str] = ['http://localhost:3000']
    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_refresh_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12

    @field_validator('cors_origins', mode='before')
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()