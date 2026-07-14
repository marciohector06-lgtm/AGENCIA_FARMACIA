import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.v1.pagination import LimitQuery, SkipQuery
from app.core.db import get_db
from app.models.agente_ia import AgenteIA
from app.models.enums import StatusAprovacaoEnum
from app.models.precificacao_historico import PrecificacaoHistorico
from app.models.produto import Produto
from app.schemas.precificacao import PrecificacaoHistoricoRead

router = APIRouter(prefix="/precificacao", tags=["precificacao"])

Proponente = aliased(AgenteIA)
Aprovador = aliased(AgenteIA)


@router.get("", response_model=list[PrecificacaoHistoricoRead])
async def listar_precificacao(
    skip: SkipQuery = 0,
    limit: LimitQuery = 50,
    status_aprovacao: StatusAprovacaoEnum | None = None,
    produto_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PrecificacaoHistoricoRead]:
    stmt = (
        select(PrecificacaoHistorico, Produto, Proponente, Aprovador)
        .join(Produto, PrecificacaoHistorico.produto_id == Produto.id)
        .join(Proponente, PrecificacaoHistorico.proposto_por_agente_id == Proponente.id)
        .outerjoin(Aprovador, PrecificacaoHistorico.aprovado_por_agente_id == Aprovador.id)
    )
    if status_aprovacao is not None:
        stmt = stmt.where(PrecificacaoHistorico.status_aprovacao == status_aprovacao)
    if produto_id is not None:
        stmt = stmt.where(PrecificacaoHistorico.produto_id == produto_id)
    stmt = stmt.order_by(PrecificacaoHistorico.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [
        PrecificacaoHistoricoRead(
            id=p.id,
            produto_id=p.produto_id,
            produto_nome=produto.nome_comercial,
            lote_id=p.lote_id,
            preco_anterior=p.preco_anterior,
            preco_novo=p.preco_novo,
            margem_resultante=p.margem_resultante,
            motivo=p.motivo,
            proposto_por_agente_id=p.proposto_por_agente_id,
            proposto_por_nome=proponente.nome,
            aprovado_por_agente_id=p.aprovado_por_agente_id,
            aprovado_por_nome=aprovador.nome if aprovador else None,
            status_aprovacao=p.status_aprovacao,
            aprovado_em=p.aprovado_em,
            created_at=p.created_at,
        )
        for p, produto, proponente, aprovador in result.all()
    ]
