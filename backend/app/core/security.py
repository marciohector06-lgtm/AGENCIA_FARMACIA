"""FASE 1 (SEC-01): primitivas de senha e JWT. Sem estado, sem I/O — só a
matemática. A decisão de quem pode logar (SELECT em operadores) vive no
endpoint de login; a decisão de "esse token é válido" vive em app/core/auth.py.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return _pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return _pwd_context.verify(senha, senha_hash)


def criar_access_token(*, sub: str, claims: dict | None = None) -> str:
    settings = get_settings()
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_expire_minutes),
        **(claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class TokenInvalidoError(Exception):
    pass


def decodificar_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenInvalidoError(str(exc)) from exc
