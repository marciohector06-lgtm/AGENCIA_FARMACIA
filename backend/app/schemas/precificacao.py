import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusAprovacaoEnum


class PrecificacaoHistoricoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    produto_id: uuid.UUID
    produto_nome: str
    lote_id: uuid.UUID | None
    preco_anterior: Decimal
    preco_novo: Decimal
    margem_resultante: Decimal | None
    motivo: str
    proposto_por_agente_id: uuid.UUID
    proposto_por_nome: str
    aprovado_por_agente_id: uuid.UUID | None
    aprovado_por_nome: str | None
    status_aprovacao: StatusAprovacaoEnum
    aprovado_em: datetime | None
    created_at: datetime
