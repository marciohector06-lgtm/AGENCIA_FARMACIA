import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.estoque import Estoque
from app.schemas.estoque import EstoqueCreate, EstoqueRead, EstoqueUpdate

router = APIRouter(prefix="/estoque", tags=["estoque"])
crud_estoque = CRUDBase[Estoque, EstoqueCreate, EstoqueUpdate](Estoque)


@router.get("", response_model=list[EstoqueRead])
async def listar_estoque(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[Estoque]:
    return await crud_estoque.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=EstoqueRead, status_code=status.HTTP_201_CREATED)
async def criar_posicao_estoque(estoque_in: EstoqueCreate, db: AsyncSession = Depends(get_db)) -> Estoque:
    try:
        return await crud_estoque.create(db, obj_in=estoque_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe posição de estoque para este lote nesta filial"
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
    estoque = await crud_estoque.get(db, estoque_id)
    if estoque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posição de estoque não encontrada")
    try:
        return await crud_estoque.update(db, db_obj=estoque, obj_in=estoque_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Reserva não pode exceder a quantidade atual"
        ) from exc
