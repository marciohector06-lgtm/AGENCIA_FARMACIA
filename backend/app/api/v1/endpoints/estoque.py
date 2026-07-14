import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.pagination import LimitQuery, SkipQuery
from app.core.db import get_db
from app.crud.base import CRUDBase
from app.crud.origem_guard import exigir_origem_editavel
from app.models.estoque import Estoque
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.schemas.estoque import EstoqueCreate, EstoqueRead, EstoqueUpdate, MovimentacaoEstoqueCreate, MovimentacaoEstoqueRead

router = APIRouter(prefix="/estoque", tags=["estoque"])
crud_estoque = CRUDBase[Estoque, EstoqueCreate, EstoqueUpdate](Estoque)


@router.get("", response_model=list[EstoqueRead])
async def listar_estoque(skip: SkipQuery = 0, limit: LimitQuery = 100, db: AsyncSession = Depends(get_db)) -> list[Estoque]:
    return await crud_estoque.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=EstoqueRead, status_code=status.HTTP_201_CREATED)
async def criar_posicao_estoque(estoque_in: EstoqueCreate, db: AsyncSession = Depends(get_db)) -> Estoque:
    try:
        return await crud_estoque.create(db, obj_in=estoque_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Posição de estoque inválida: verifique se já existe uma posição para este lote nesta filial, "
                "e se a quantidade reservada não excede a quantidade atual"
            ),
        ) from exc


@router.get("/{estoque_id}", response_model=EstoqueRead)
async def obter_posicao_estoque(estoque_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Estoque:
    estoque = await crud_estoque.get(db, estoque_id)
    if estoque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posição de estoque não encontrada")
    return estoque


@router.patch("/{estoque_id}", response_model=EstoqueRead)
async def atualizar_posicao_estoque(
    estoque_id: uuid.UUID, estoque_in: EstoqueUpdate, db: AsyncSession = Depends(get_db)
) -> Estoque:
    """Só localizacao_gondola passa por aqui (ver EstoqueUpdate/SEC-11) — quantidade
    muda exclusivamente via POST /estoque/{id}/movimentar."""
    estoque = await crud_estoque.get(db, estoque_id)
    if estoque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posição de estoque não encontrada")
    exigir_origem_editavel(estoque)
    try:
        return await crud_estoque.update(db, db_obj=estoque, obj_in=estoque_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Atualização inválida") from exc


@router.post("/{estoque_id}/movimentar", response_model=MovimentacaoEstoqueRead, status_code=status.HTTP_201_CREATED)
async def movimentar_estoque(
    estoque_id: uuid.UUID, movimentacao_in: MovimentacaoEstoqueCreate, db: AsyncSession = Depends(get_db)
) -> MovimentacaoEstoque:
    """Única forma de alterar quantidade_atual após a criação da posição de
    estoque (SEC-11). Só permitido para origem='manual': estoque sincronizado
    de um ERP muda de quantidade só pelo próximo sync (F0-07), nunca por um
    humano digitando um número aqui — o ERP é quem sabe a verdade.

    `with_for_update()` trava a linha até o commit: duas movimentações
    concorrentes na mesma posição de estoque serializam aqui em vez de correr
    o risco de uma pisar na outra (mesma lógica do débito de venda em
    service.py::_debitar_estoque_venda).
    """
    estoque = (
        await db.execute(select(Estoque).where(Estoque.id == estoque_id).with_for_update())
    ).scalar_one_or_none()
    if estoque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posição de estoque não encontrada")
    exigir_origem_editavel(estoque)

    nova_quantidade = estoque.quantidade_atual + movimentacao_in.quantidade_delta
    if nova_quantidade < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Movimentação deixaria o estoque negativo (atual={estoque.quantidade_atual}, delta={movimentacao_in.quantidade_delta}).",
        )

    estoque.quantidade_atual = nova_quantidade
    movimentacao = MovimentacaoEstoque(
        estoque_id=estoque.id,
        tipo=movimentacao_in.tipo,
        quantidade_delta=movimentacao_in.quantidade_delta,
        quantidade_resultante=nova_quantidade,
        motivo=movimentacao_in.motivo,
    )
    db.add(movimentacao)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movimentação inválida") from exc
    await db.refresh(movimentacao)
    return movimentacao
