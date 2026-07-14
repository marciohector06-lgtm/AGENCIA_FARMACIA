import uuid

from pydantic import BaseModel, Field


class AnaliseEstoqueRequest(BaseModel):
    filial_id: uuid.UUID | None = None
    dias_vencimento: int = Field(default=60, ge=1, le=365)


class DecisaoPrecificacaoResumo(BaseModel):
    precificacao_id: uuid.UUID
    aprovado: bool
    margem_resultante: float | None = None
    justificativa: str


class AnaliseEstoqueResponse(BaseModel):
    propostas_geradas: int
    aprovadas: int
    rejeitadas: int
    decisoes: list[DecisaoPrecificacaoResumo]
    resumo: str
    log_auditoria_ids: list[uuid.UUID]
