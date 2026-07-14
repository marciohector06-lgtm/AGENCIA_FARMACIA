import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.pagination import LimitQuery, SkipQuery
from app.core.db import get_db
from app.models.agente_ia import AgenteIA
from app.models.enums import TipoDecisaoEnum
from app.models.log_auditoria import LogAuditoria
from app.schemas.auditoria import LogAuditoriaRead

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=list[LogAuditoriaRead])
async def listar_auditoria(
    skip: SkipQuery = 0,
    limit: LimitQuery = 50,
    tipo_decisao: TipoDecisaoEnum | None = None,
    agente_id: uuid.UUID | None = None,
    sessao_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[LogAuditoriaRead]:
    stmt = select(LogAuditoria, AgenteIA).join(AgenteIA, LogAuditoria.agente_id == AgenteIA.id)
    if tipo_decisao is not None:
        stmt = stmt.where(LogAuditoria.tipo_decisao == tipo_decisao)
    if agente_id is not None:
        stmt = stmt.where(LogAuditoria.agente_id == agente_id)
    if sessao_id is not None:
        stmt = stmt.where(LogAuditoria.sessao_id == sessao_id)
    stmt = stmt.order_by(LogAuditoria.criado_em.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [
        LogAuditoriaRead(
            id=log.id,
            agente_id=log.agente_id,
            agente_nome=agente.nome,
            agente_tipo=agente.tipo.value,
            tipo_decisao=log.tipo_decisao,
            entidade_afetada=log.entidade_afetada,
            entidade_id=log.entidade_id,
            principio_ativo_id=log.principio_ativo_id,
            decisao_tomada=log.decisao_tomada,
            dados_base=log.dados_base,
            justificativa=log.justificativa,
            confianca=float(log.confianca) if log.confianca is not None else None,
            sessao_id=log.sessao_id,
            criado_em=log.criado_em,
        )
        for log, agente in result.all()
    ]
