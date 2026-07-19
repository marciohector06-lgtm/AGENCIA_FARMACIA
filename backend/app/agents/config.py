from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentRole(str, Enum):
    ATENDENTE = "atendente"
    GERENTE_ESTOQUE = "gerente_estoque"
    FINANCEIRO = "financeiro"
    ORQUESTRADOR = "orquestrador"
    TRIBUTARIO = "tributario"


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Uma connection string síncrona por role de agente (nunca app_backend).
    # Cada uma herda o RLS/GRANT definido na FASE 1 para aquela role específica.
    database_url_agente_atendente: str
    database_url_agente_estoque: str
    database_url_agente_financeiro: str
    database_url_agente_orquestrador: str
    database_url_agente_tributario: str

    # Mesma flag usada pelo backend (app/core/config.py): Supabase exige TLS em
    # conexão direta, mas um Postgres local de desenvolvimento normalmente não
    # suporta SSL. Nunca hardcode sslmode=require sem checar isto.
    db_ssl_require: bool = True

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # gemini-1.5-pro e gemini-2.5-pro/flash foram descontinuados pela Google
    # (a versão numerada para de responder pra contas novas, 404 NOT_FOUND —
    # foi o que quebrou o atendimento em produção em 2026-07-18). Usa os
    # aliases -latest, que a Google migra automaticamente pro modelo vigente
    # daquele nível — evita esse mesmo apagão a cada aposentadoria de versão.
    # Ajustável via GEMINI_MODEL.
    gemini_model: str = "gemini/gemini-pro-latest"
    # LLM-10: o atendente faz regra rígida + structured output em alto volume
    # (é o endpoint com rate limit mais alto, SEC-02) — não precisa do
    # raciocínio pesado do Pro. Gerente/financeiro/orquestrador continuam Pro.
    gemini_model_atendente: str = "gemini/gemini-flash-latest"
    groq_model: str = "groq/llama3-70b-8192"

    # LLM-05: timeout de crew.kickoff() — ver app/agents/execucao.py.
    crew_timeout_seconds: float = 90.0

    # Agente Tributário (Bloco 1): credenciais IMAP do email corporativo que
    # recebe as NF-e. Vazio por padrão — LerEmailNFesTool falha cedo e com
    # mensagem clara se disparado sem isso configurado, em vez de um erro
    # obscuro de conexão IMAP.
    nfe_email_host: str = ""
    nfe_email_user: str = ""
    nfe_email_password: str = ""
    # Só documentação/uso futuro por um cron — o Bloco 1 não agenda nada
    # sozinho, só expõe o disparo manual (POST /agentes/processar-nfe-email).
    nfe_horario_processamento: str = "18:00"

    def database_url_for(self, role: AgentRole) -> str:
        return {
            AgentRole.ATENDENTE: self.database_url_agente_atendente,
            AgentRole.GERENTE_ESTOQUE: self.database_url_agente_estoque,
            AgentRole.FINANCEIRO: self.database_url_agente_financeiro,
            AgentRole.ORQUESTRADOR: self.database_url_agente_orquestrador,
            AgentRole.TRIBUTARIO: self.database_url_agente_tributario,
        }[role]

    def llm_model_id(self, role: AgentRole | None = None) -> str:
        if self.llm_provider == "groq":
            if not self.groq_api_key:
                raise RuntimeError("LLM_PROVIDER=groq mas GROQ_API_KEY não está definida no .env")
            return self.groq_model
        if not self.gemini_api_key:
            raise RuntimeError("LLM_PROVIDER=gemini mas GEMINI_API_KEY não está definida no .env")
        if role == AgentRole.ATENDENTE:
            return self.gemini_model_atendente
        return self.gemini_model


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
