import threading
import uuid

from cachetools import TTLCache, cached
from sqlalchemy import select

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.models.agente_ia import AgenteIA
from app.models.enums import TipoAgenteEnum

ROLE_TO_TIPO_AGENTE: dict[AgentRole, TipoAgenteEnum] = {
    AgentRole.ATENDENTE: TipoAgenteEnum.atendente,
    AgentRole.GERENTE_ESTOQUE: TipoAgenteEnum.gerente_estoque,
    AgentRole.FINANCEIRO: TipoAgenteEnum.financeiro,
    AgentRole.ORQUESTRADOR: TipoAgenteEnum.orquestrador,
}

# LLM-09: lru_cache (sem maxsize e sem expiração) mantinha o id do agente em
# memória para sempre — se uma linha de agentes_ia for desativada/trocada
# (ex.: rotação do agente "atendente" para uma nova linha), o processo nunca
# via a mudança até reiniciar. TTL de 5 min é o meio-termo entre "não bater
# no banco a cada chamada" e "não servir um id morto indefinidamente". Lock
# porque TTLCache não é thread-safe e agente_id_for roda dentro das threads
# auxiliares do ThreadPoolExecutor de executar_crew (app/agents/execucao.py).
_agente_id_cache: TTLCache = TTLCache(maxsize=8, ttl=300)
_agente_id_cache_lock = threading.Lock()


@cached(cache=_agente_id_cache, lock=_agente_id_cache_lock)
def agente_id_for(role: AgentRole) -> uuid.UUID:
    """Resolve o id em agentes_ia para a role, obrigatório em toda migration 0015."""
    with agent_session(role) as session:
        tipo = ROLE_TO_TIPO_AGENTE[role]
        agente = session.execute(select(AgenteIA).where(AgenteIA.tipo == tipo, AgenteIA.ativo)).scalars().first()
        if agente is None:
            raise RuntimeError(
                f"Nenhuma linha ativa em agentes_ia para tipo='{tipo.value}'. "
                "Rode database/migrations/0015_seed_agentes.sql."
            )
        return agente.id
