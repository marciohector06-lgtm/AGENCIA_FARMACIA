import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.fabricante import Fabricante
from app.schemas.fabricante import FabricanteCreate, FabricanteRead, FabricanteUpdate

router = APIRouter(prefix="/fabricantes", tags=["fabricantes"])
crud_fabricante = CRUDBase[Fabricante, FabricanteCreate, FabricanteUpdate](Fabricante)


@router.get("", response_model=list[FabricanteRead])
async def listar_fabricantes(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Fabricante]:
    return await crud_fabricante.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=FabricanteRead, status_code=status.HTTP_201_CREATED)
async def criar_fabricante(fabricante_in: FabricanteCreate, db: AsyncSession = Depends(get_db)) -> Fabricante:
    try:
        return await crud_fabricante.create(db, obj_in=fabricante_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Fabricante já existe (CNPJ duplicado?)"
        ) from exc


@router.get("/{fabricante_id}", response_model=FabricanteRead)
async def obter_fabricante(fabricante_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Fabricante:
    fabricante = await crud_fabricante.get(db, fabricante_id)
    if fabricante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabricante não encontrado")
    return fabricante


@router.patch("/{fabricante_id}", response_model=FabricanteRead)
async def atualizar_fabricante(
    fabricante_id: uuid.UUID, fabricante_in: FabricanteUpdate, db: AsyncSession = Depends(get_db)
) -> Fabricante:
    fabricante = await crud_fabricante.get(db, fabricante_id)
    if fabricante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabricante não encontrado")
    return await crud_fabricante.update(db, db_obj=fabricante, obj_in=fabricante_in)


@router.delete("/{fabricante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_fabricante(fabricante_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    fabricante = await crud_fabricante.get(db, fabricante_id)
    if fabricante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabricante não encontrado")
    await crud_fabricante.remove(db, db_obj=fabricante)
