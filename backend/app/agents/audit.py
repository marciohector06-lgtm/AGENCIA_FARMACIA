import uuid
from typing import Any

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.agents.registry import agente_id_for
from app.models.enums import TipoDecisaoEnum
from app.models.log_auditoria import LogAuditoria


def registrar_auditoria(
    *,
    role: AgentRole,
    tipo_decisao: TipoDecisaoEnum,
    entidade_afetada: str,
    decisao_tomada: str,
    dados_base: dict[str, Any],
    entidade_id: uuid.UUID | None = None,
    principio_ativo_id: uuid.UUID | None = None,
    justificativa: str | None = None,
    confianca: float | None = None,
    sessao_id: uuid.UUID | None = None,
    modelo_llm: str | None = None,
    tokens_totais: int | None = None,
    latencia_ms: int | None = None,
    pseudonimo_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Grava uma linha em logs_auditoria, sempre pela role do próprio agente que decidiu.

    Chamada deterministicamente pela camada de serviço (app/agents/service.py)
    após cada decisão autônoma — nunca depende do LLM "lembrar" de registrar.

    modelo_llm/tokens_totais/latencia_ms (LLM-08/QA-03): só preenchidos por
    chamadas originadas de uma execução de crew (ver app/agents/execucao.py)
    — None em decisões determinísticas puras (sync, movimentação de estoque).
    """
    with agent_session(role) as session:
        log = LogAuditoria(
            agente_id=agente_id_for(role),
            tipo_decisao=tipo_decisao,
            entidade_afetada=entidade_afetada,
            entidade_id=entidade_id,
            principio_ativo_id=principio_ativo_id,
            decisao_tomada=decisao_tomada,
            dados_base=dados_base,
            justificativa=justificativa,
            confianca=confianca,
            sessao_id=sessao_id,
            modelo_llm=modelo_llm,
            tokens_totais=tokens_totais,
            latencia_ms=latencia_ms,
            pseudonimo_id=pseudonimo_id,
        )
        session.add(log)
        session.flush()
        return log.id
