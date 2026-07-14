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

    # FASE 0: qual ERPAdapter esta instalação usa (app/integrations/registry.py).
    # "mock" é o único implementado por enquanto — ver app/integrations/mock_adapter.py.
    erp_provider: str = "mock"

    # FASE 1 (SEC-01): endpoint de tarja agora exige Depends(get_current_operador)
    # (ver app/core/auth.py) — a flag continua existindo como kill-switch
    # adicional, mas o default já é True porque a pré-condição dela (auth no
    # ar) foi satisfeita nesta fase.
    tarja_endpoint_enabled: bool = True

    # FASE 1 (SEC-01): sem default — força um segredo real via .env/ambiente,
    # nunca um valor hardcoded previsível. Gere com:
    #   python -c "import secrets; print(secrets.token_urlsafe(32))"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
