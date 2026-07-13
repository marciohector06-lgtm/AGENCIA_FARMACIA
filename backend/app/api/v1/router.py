from fastapi import APIRouter

from app.api.v1.endpoints import (
    agentes,
    auditoria,
    chat,
    clientes,
    estoque,
    fabricantes,
    filiais,
    lotes,
    precificacao,
    principios_ativos,
    produtos,
)

api_router = APIRouter()
api_router.include_router(filiais.router)
api_router.include_router(fabricantes.router)
api_router.include_router(principios_ativos.router)
api_router.include_router(produtos.router)
api_router.include_router(lotes.router)
api_router.include_router(estoque.router)
api_router.include_router(clientes.router)
api_router.include_router(agentes.router)
api_router.include_router(chat.router)
api_router.include_router(auditoria.router)
api_router.include_router(precificacao.router)
