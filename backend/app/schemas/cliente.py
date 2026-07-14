import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    nome: str
    cpf: str | None = None
    data_nascimento: date | None = None
    telefone: str | None = None
    email: str | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: str | None = None
    cpf: str | None = None
    data_nascimento: date | None = None
    telefone: str | None = None
    email: str | None = None


class ClienteRead(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # LGPD-03: só muda via POST /clientes/{id}/consentimento — nunca pelo
    # ClienteUpdate/PATCH acima (de propósito: não faz parte dele).
    consentimento_dado: bool
    consentimento_lgpd_em: datetime | None = None
