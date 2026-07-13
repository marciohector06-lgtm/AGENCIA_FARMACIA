import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import TipoDecisaoEnum


class LogAuditoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agente_id: uuid.UUID
    agente_nome: str
    agente_tipo: str
    tipo_decisao: TipoDecisaoEnum
    entidade_afetada: str
    entidade_id: uuid.UUID | None
    principio_ativo_id: uuid.UUID | None
    decisao_tomada: str
    dados_base: dict[str, Any]
    justificativa: str | None
    confianca: float | None
    sessao_id: uuid.UUID | None
    criado_em: datetime
