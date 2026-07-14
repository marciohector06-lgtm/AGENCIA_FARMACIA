from crewai import LLM

from app.agents.config import AgentRole, get_agent_settings


def build_llm(temperature: float = 0.2, role: AgentRole | None = None) -> LLM:
    """Instancia o LLM conforme LLM_PROVIDER, resolvendo o modelo por role
    (LLM-10: atendente usa Gemini Flash, os demais usam Pro — ver
    AgentSettings.llm_model_id).

    Levanta RuntimeError cedo (via get_agent_settings().llm_model_id()) se a
    chave de API do provedor escolhido não estiver configurada, em vez de
    deixar o crew falhar de forma obscura no meio de uma tarefa.
    """
    settings = get_agent_settings()
    model_id = settings.llm_model_id(role)
    api_key = settings.groq_api_key if settings.llm_provider == "groq" else settings.gemini_api_key
    return LLM(model=model_id, api_key=api_key, temperature=temperature)
