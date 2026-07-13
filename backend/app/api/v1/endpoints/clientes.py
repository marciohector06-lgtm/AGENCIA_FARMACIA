import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteRead, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["clientes"])
crud_cliente = CRUDBase[Cliente, ClienteCreate, ClienteUpdate](Cliente)


@router.get("", response_model=list[ClienteRead])
async def listar_clientes(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[Cliente]:
    return await crud_cliente.get_multi(db, skip=skip, limit=limit)


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente_in: ClienteCreate, db: AsyncSession = Depends(get_db)) -> Cliente:
    try:
        return await crud_cliente.create(db, obj_in=cliente_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cliente já cadastrado (CPF duplicado?)"
        ) from exc


@router.get("/{cliente_id}", response_model=ClienteRead)
async def obter_cliente(cliente_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Cliente:
    cliente = await crud_cliente.get(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return cliente


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def atualizar_cliente(
    cliente_id: uuid.UUID, cliente_in: ClienteUpdate, db: AsyncSession = Depends(get_db)
) -> Cliente:
    cliente = await crud_cliente.get(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return await crud_cliente.update(db, db_obj=cliente, obj_in=cliente_in)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_cliente(cliente_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    cliente = await crud_cliente.get(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    await crud_cliente.remove(db, db_obj=cliente)
