import uuid

from pydantic import BaseModel, ConfigDict


class EstoqueBase(BaseModel):
    filial_id: uuid.UUID
    lote_id: uuid.UUID
    quantidade_atual: int = 0
    quantidade_reservada: int = 0
    localizacao_gondola: str | None = None


class EstoqueCreate(EstoqueBase):
    pass


class EstoqueUpdate(BaseModel):
    quantidade_atual: int | None = None
    quantidade_reservada: int | None = None
    localizacao_gondola: str | None = None


class EstoqueRead(EstoqueBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
