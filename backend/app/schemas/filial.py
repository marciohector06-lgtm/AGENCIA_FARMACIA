import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FilialBase(BaseModel):
    nome: str
    cnpj: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    ativo: bool = True


class FilialCreate(FilialBase):
    pass


class FilialUpdate(BaseModel):
    nome: str | None = None
    cnpj: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    ativo: bool | None = None


class FilialRead(FilialBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_externo: str | None = None
    origem: str
    sincronizado_em: datetime | None = None
