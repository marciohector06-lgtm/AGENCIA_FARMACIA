from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentRole(str, Enum):
    ATENDENTE = "atendente"
    GERENTE_ESTOQUE = "gerente_estoque"
    FINANCEIRO = "financeiro"
    ORQUESTRADOR = "orquestrador"


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Uma connection string síncrona por role de agente (nunca app_backend).
    # Cada uma herda o RLS/GRANT definido na FASE 1 para aquela role específica.
    database_url_agente_atendente: str
    database_url_agente_estoque: str
    database_url_agente_financeiro: str
    database_url_agente_orquestrador: str

    # Mesma flag usada pelo backend (app/core/config.py): Supabase exige TLS em
    # conexão direta, mas um Postgres local de desenvolvimento normalmente não
    # suporta SSL. Nunca hardcode sslmode=require sem checar isto.
    db_ssl_require: bool = True

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # gemini-1.5-pro foi descontinuado pela Google; gemini-2.5-pro é o
    # equivalente atual em capacidade de raciocínio. Ajustável via GEMINI_MODEL.
    gemini_model: str = "gemini/gemini-2.5-pro"
    groq_model: str = "groq/llama3-70b-8192"

    def database_url_for(self, role: AgentRole) -> str:
        return {
            AgentRole.ATENDENTE: self.database_url_agente_atendente,
            AgentRole.GERENTE_ESTOQUE: self.database_url_agente_estoque,
            AgentRole.FINANCEIRO: self.database_url_agente_financeiro,
            AgentRole.ORQUESTRADOR: self.database_url_agente_orquestrador,
        }[role]

    def llm_model_id(self) -> str:
        if self.llm_provider == "groq":
            if not self.groq_api_key:
                raise RuntimeError("LLM_PROVIDER=groq mas GROQ_API_KEY não está definida no .env")
            return self.groq_model
        if not self.gemini_api_key:
            raise RuntimeError("LLM_PROVIDER=gemini mas GEMINI_API_KEY não está definida no .env")
        return self.gemini_model


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
