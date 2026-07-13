import uuid
from functools import lru_cache

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


@lru_cache
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
