import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.filial import Filial
from app.schemas.filial import FilialCreate, FilialRead, FilialUpdate

router = APIRouter(prefix="/filiais", tags=["filiais"])
crud_filial = CRUDBase[Filial, FilialCreate, FilialUpdate](Filial)


@router.get("", response_model=list[FilialRead])
async def listar_filiais(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[Filial]:
    return await crud_filial.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=FilialRead, status_code=status.HTTP_201_CREATED)
async def criar_filial(filial_in: FilialCreate, db: AsyncSession = Depends(get_db)) -> Filial:
    try:
        return await crud_filial.create(db, obj_in=filial_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Filial já existe (CNPJ duplicado?)") from exc


@router.get("/{filial_id}", response_model=FilialRead)
async def obter_filial(filial_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Filial:
    filial = await crud_filial.get(db, filial_id)
    if filial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filial não encontrada")
    return filial


@router.patch("/{filial_id}", response_model=FilialRead)
async def atualizar_filial(
    filial_id: uuid.UUID, filial_in: FilialUpdate, db: AsyncSession = Depends(get_db)
) -> Filial:
    filial = await crud_filial.get(db, filial_id)
    if filial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filial não encontrada")
    return await crud_filial.update(db, db_obj=filial, obj_in=filial_in)


@router.delete("/{filial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_filial(filial_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    filial = await crud_filial.get(db, filial_id)
    if filial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filial não encontrada")
    await crud_filial.remove(db, db_obj=filial)
