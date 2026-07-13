from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Sem valor padrão: força a existência de um .env real (ou variável de
    # ambiente) com a credencial da role app_backend. Nunca cai silenciosamente
    # em um segredo hardcoded.
    database_url: str
    db_echo: bool = False
    db_ssl_require: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
