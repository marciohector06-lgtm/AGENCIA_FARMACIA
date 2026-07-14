from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    agentes,
    auditoria,
    auth,
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
from app.core.auth import get_current_operador

api_router = APIRouter()

# /auth/login é o único jeito de conseguir um token — não pode exigir um.
api_router.include_router(auth.router)

# FASE 1 (SEC-01): todo o resto exige Bearer token válido. /health continua
# de fora porque é montado direto em app/main.py, sem passar por api_router.
protegido_router = APIRouter(dependencies=[Depends(get_current_operador)])
protegido_router.include_router(filiais.router)
protegido_router.include_router(fabricantes.router)
protegido_router.include_router(principios_ativos.router)
protegido_router.include_router(produtos.router)
protegido_router.include_router(lotes.router)
protegido_router.include_router(estoque.router)
protegido_router.include_router(clientes.router)
protegido_router.include_router(agentes.router)
protegido_router.include_router(chat.router)
protegido_router.include_router(auditoria.router)
protegido_router.include_router(precificacao.router)

api_router.include_router(protegido_router)
