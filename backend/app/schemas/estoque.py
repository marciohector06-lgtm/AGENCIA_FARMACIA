import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TipoMovimentacaoEnum


class EstoqueBase(BaseModel):
    filial_id: uuid.UUID
    lote_id: uuid.UUID
    # Só permitido na CRIAÇÃO (entrada inicial de um lote que ainda não tem
    # posição de estoque). Depois de criado, quantidade só muda por
    # movimentação — ver MovimentacaoEstoqueCreate e SEC-11.
    quantidade_atual: int = 0
    quantidade_reservada: int = 0
    localizacao_gondola: str | None = None


class EstoqueCreate(EstoqueBase):
    pass


class EstoqueUpdate(BaseModel):
    # SEC-11: quantidade_atual/quantidade_reservada NUNCA são editáveis por
    # PATCH direto — isso permitia fabricar estoque infinito via API sem
    # nenhuma tool de agente envolvida. A única forma de mudar quantidade após
    # a criação é POST /estoque/{id}/movimentar (motivo obrigatório).
    localizacao_gondola: str | None = None


class EstoqueRead(EstoqueBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_externo: str | None = None
    origem: str
    sincronizado_em: datetime | None = None


class MovimentacaoEstoqueCreate(BaseModel):
    # "venda" é reservado para o débito interno feito pelo fluxo de
    # atendimento (F0-06) — não é um tipo aceito neste endpoint manual.
    tipo: TipoMovimentacaoEnum = Field(default=TipoMovimentacaoEnum.ajuste)
    quantidade_delta: int = Field(description="Positivo para entrada, negativo para saída/ajuste para baixo")
    motivo: str = Field(min_length=10)


class MovimentacaoEstoqueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estoque_id: uuid.UUID
    tipo: TipoMovimentacaoEnum
    quantidade_delta: int
    quantidade_resultante: int
    motivo: str
    venda_id: uuid.UUID | None = None
    criado_em: datetime
