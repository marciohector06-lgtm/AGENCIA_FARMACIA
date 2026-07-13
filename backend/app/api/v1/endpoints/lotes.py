import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.lote import Lote
from app.schemas.lote import LoteCreate, LoteRead, LoteUpdate

router = APIRouter(prefix="/lotes", tags=["lotes"])
crud_lote = CRUDBase[Lote, LoteCreate, LoteUpdate](Lote)


@router.get("", response_model=list[LoteRead])
async def listar_lotes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[Lote]:
    return await crud_lote.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=LoteRead, status_code=status.HTTP_201_CREATED)
async def criar_lote(lote_in: LoteCreate, db: AsyncSession = Depends(get_db)) -> Lote:
    try:
        return await crud_lote.create(db, obj_in=lote_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lote inválido: número de lote duplicado para este produto ou validade anterior à fabricação",
        ) from exc


@router.get("/{lote_id}", response_model=LoteRead)
async def obter_lote(lote_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Lote:
    lote = await crud_lote.get(db, lote_id)
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote não encontrado")
    return lote


@router.patch("/{lote_id}", response_model=LoteRead)
async def atualizar_status_lote(
    lote_id: uuid.UUID, lote_in: LoteUpdate, db: AsyncSession = Depends(get_db)
) -> Lote:
    lote = await crud_lote.get(db, lote_id)
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote não encontrado")
    return await crud_lote.update(db, db_obj=lote, obj_in=lote_in)
