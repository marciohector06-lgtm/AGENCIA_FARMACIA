"""FASE 1 (SEC-01): "token válido entra, token inválido retorna 401." Nada
além disso — sem lookup em banco a cada request (o JWT já carrega o que
precisamos) e sem permissões finas (isso é decisão de fase futura).
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import TokenInvalidoError, decodificar_access_token

# auto_error=False: sem isso, HTTPBearer devolve 403 quando o header
# Authorization está ausente. Queremos 401 nos dois casos (ausente ou
# inválido) — semântica correta é "não autenticado", não "não autorizado".
_bearer_scheme = HTTPBearer(auto_error=False)

_NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class OperadorAutenticado:
    operador_id: str
    email: str | None


def get_current_operador(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> OperadorAutenticado:
    if credentials is None:
        raise _NAO_AUTENTICADO
    try:
        payload = decodificar_access_token(credentials.credentials)
    except TokenInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    operador_id = payload.get("sub")
    if not operador_id:
        raise _NAO_AUTENTICADO
    return OperadorAutenticado(operador_id=operador_id, email=payload.get("email"))
