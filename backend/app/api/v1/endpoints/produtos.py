import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.audit import registrar_auditoria
from app.agents.config import AgentRole
from app.api.v1.pagination import LimitQuery, SkipQuery
from app.core.auth import OperadorAutenticado, get_current_operador
from app.core.config import get_settings
from app.core.db import get_db
from app.crud.base import CRUDBase
from app.crud.origem_guard import exigir_origem_editavel
from app.models.enums import TarjaEnum, TipoDecisaoEnum
from app.models.produto import Produto
from app.schemas.produto import ProdutoCreate, ProdutoRead, ProdutoTarjaUpdate, ProdutoUpdate

router = APIRouter(prefix="/produtos", tags=["produtos"])
crud_produto = CRUDBase[Produto, ProdutoCreate, ProdutoUpdate](Produto)


@router.get("", response_model=list[ProdutoRead])
async def listar_produtos(
    skip: SkipQuery = 0,
    limit: LimitQuery = 100,
    ativo: bool | None = None,
    tarja: TarjaEnum | None = None,
    principio_ativo_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Produto]:
    stmt = select(Produto)
    if ativo is not None:
        stmt = stmt.where(Produto.ativo == ativo)
    if tarja is not None:
        stmt = stmt.where(Produto.tarja == tarja)
    if principio_ativo_id is not None:
        stmt = stmt.where(Produto.principio_ativo_id == principio_ativo_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ProdutoRead, status_code=status.HTTP_201_CREATED)
async def criar_produto(produto_in: ProdutoCreate, db: AsyncSession = Depends(get_db)) -> Produto:
    try:
        return await crud_produto.create(db, obj_in=produto_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Produto inválido: verifique código de barras duplicado ou princípio "
                "ativo obrigatório para esta forma farmacêutica"
            ),
        ) from exc


@router.get("/{produto_id}", response_model=ProdutoRead)
async def obter_produto(produto_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Produto:
    produto = await crud_produto.get(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return produto


@router.patch("/{produto_id}", response_model=ProdutoRead)
async def atualizar_produto(
    produto_id: uuid.UUID, produto_in: ProdutoUpdate, db: AsyncSession = Depends(get_db)
) -> Produto:
    produto = await crud_produto.get(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    exigir_origem_editavel(produto)
    try:
        return await crud_produto.update(db, db_obj=produto, obj_in=produto_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Atualização inválida") from exc


@router.patch("/{produto_id}/tarja", response_model=ProdutoRead)
async def alterar_tarja_produto(
    produto_id: uuid.UUID,
    tarja_in: ProdutoTarjaUpdate,
    db: AsyncSession = Depends(get_db),
    operador: OperadorAutenticado = Depends(get_current_operador),
) -> Produto:
    """Exceção inegociável (independe de origem): tarja NUNCA muda por PATCH
    comum. É a única fronteira entre um produto ser vendável pelo agente
    atendente (RLS de 0012 filtra por tarja='isento') ou não — toda mudança
    passa por aqui e é sempre registrada em logs_auditoria.

    FASE 1 (SEC-01/SEC-06): `operador` já vem exigido pelo dependencies=[...]
    de nível de router (app/api/v1/router.py) — está repetido aqui de
    propósito, como documentação executável: este endpoint específico é
    perigoso demais pra depender só de alguém lembrar de configurar o router
    certo. TARJA_ENDPOINT_ENABLED continua existindo como kill-switch extra
    (default True agora que a pré-condição — auth no ar — foi satisfeita).
    """
    if not get_settings().tarja_endpoint_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint desabilitado via TARJA_ENDPOINT_ENABLED=false.",
        )

    produto = await crud_produto.get(db, produto_id)
    if produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")

    tarja_anterior = produto.tarja
    produto.tarja = tarja_in.tarja
    await db.commit()
    await db.refresh(produto)

    await asyncio.to_thread(
        registrar_auditoria,
        role=AgentRole.ORQUESTRADOR,
        tipo_decisao=TipoDecisaoEnum.alteracao_tarja,
        entidade_afetada="produtos",
        entidade_id=produto.id,
        decisao_tomada=f"Tarja alterada manualmente de '{tarja_anterior.value}' para '{tarja_in.tarja.value}'.",
        dados_base={
            "produto_id": str(produto.id),
            "nome_comercial": produto.nome_comercial,
            "tarja_anterior": tarja_anterior.value,
            "tarja_nova": tarja_in.tarja.value,
            "operador_id": operador.operador_id,
            "operador_email": operador.email,
        },
        justificativa=tarja_in.motivo,
    )
    return produto
