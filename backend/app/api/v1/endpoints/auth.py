from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import criar_access_token, verificar_senha
from app.models.operador import Operador
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_CREDENCIAIS_INVALIDAS = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    operador = (
        (await db.execute(select(Operador).where(Operador.email == payload.email))).scalars().first()
    )
    # Mesma mensagem genérica pra e-mail inexistente e senha errada — não dar
    # pista sobre qual dos dois estava errado (evita enumeração de e-mails).
    if operador is None or not operador.ativo or not verificar_senha(payload.senha, operador.senha_hash):
        raise _CREDENCIAIS_INVALIDAS

    token = criar_access_token(sub=str(operador.id), claims={"email": operador.email})
    return TokenResponse(access_token=token)
