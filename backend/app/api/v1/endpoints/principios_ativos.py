import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.principio_ativo import PrincipioAtivo
from app.schemas.principio_ativo import PrincipioAtivoCreate, PrincipioAtivoRead, PrincipioAtivoUpdate

router = APIRouter(prefix="/principios-ativos", tags=["principios_ativos"])
crud_principio_ativo = CRUDBase[PrincipioAtivo, PrincipioAtivoCreate, PrincipioAtivoUpdate](PrincipioAtivo)


@router.get("", response_model=list[PrincipioAtivoRead])
async def listar_principios_ativos(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[PrincipioAtivo]:
    return await crud_principio_ativo.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=PrincipioAtivoRead, status_code=status.HTTP_201_CREATED)
async def criar_principio_ativo(
    principio_in: PrincipioAtivoCreate, db: AsyncSession = Depends(get_db)
) -> PrincipioAtivo:
    try:
        return await crud_principio_ativo.create(db, obj_in=principio_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Princípio ativo já cadastrado") from exc


@router.get("/{principio_id}", response_model=PrincipioAtivoRead)
async def obter_principio_ativo(principio_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PrincipioAtivo:
    principio = await crud_principio_ativo.get(db, principio_id)
    if principio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Princípio ativo não encontrado")
    return principio


@router.patch("/{principio_id}", response_model=PrincipioAtivoRead)
async def atualizar_principio_ativo(
    principio_id: uuid.UUID, principio_in: PrincipioAtivoUpdate, db: AsyncSession = Depends(get_db)
) -> PrincipioAtivo:
    principio = await crud_principio_ativo.get(db, principio_id)
    if principio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Princípio ativo não encontrado")
    return await crud_principio_ativo.update(db, db_obj=principio, obj_in=principio_in)
