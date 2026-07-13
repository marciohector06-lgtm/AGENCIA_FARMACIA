from crewai import LLM

from app.agents.config import get_agent_settings


def build_llm(temperature: float = 0.2) -> LLM:
    """Instancia o LLM (Gemini 1.5 Pro ou Llama 3 via Groq) conforme LLM_PROVIDER.

    Levanta RuntimeError cedo (via get_agent_settings().llm_model_id()) se a
    chave de API do provedor escolhido não estiver configurada, em vez de
    deixar o crew falhar de forma obscura no meio de uma tarefa.
    """
    settings = get_agent_settings()
    model_id = settings.llm_model_id()
    api_key = settings.groq_api_key if settings.llm_provider == "groq" else settings.gemini_api_key
    return LLM(model=model_id, api_key=api_key, temperature=temperature)
