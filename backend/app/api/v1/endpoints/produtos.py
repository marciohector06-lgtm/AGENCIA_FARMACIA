import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crud.base import CRUDBase
from app.models.enums import TarjaEnum
from app.models.produto import Produto
from app.schemas.produto import ProdutoCreate, ProdutoRead, ProdutoUpdate

router = APIRouter(prefix="/produtos", tags=["produtos"])
crud_produto = CRUDBase[Produto, ProdutoCreate, ProdutoUpdate](Produto)


@router.get("", response_model=list[ProdutoRead])
async def listar_produtos(
    skip: int = 0,
    limit: int = 100,
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
    try:
        return await crud_produto.update(db, db_obj=produto, obj_in=produto_in)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Atualização inválida") from exc
