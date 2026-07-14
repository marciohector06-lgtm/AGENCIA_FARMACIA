import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusLoteEnum


class LoteBase(BaseModel):
    produto_id: uuid.UUID
    numero_lote: str
    data_fabricacao: date
    data_validade: date
    quantidade_recebida: int
    custo_unitario: Decimal
    status: StatusLoteEnum = StatusLoteEnum.disponivel


class LoteCreate(LoteBase):
    pass


class LoteUpdate(BaseModel):
    # Deliberadamente limitado a status: fabricação/validade/custo de um lote já
    # recebido não devem mudar (mesma regra aplicada nos GRANTs da migration 0011).
    status: StatusLoteEnum | None = None


class LoteRead(LoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_externo: str | None = None
    origem: str
    sincronizado_em: datetime | None = None
