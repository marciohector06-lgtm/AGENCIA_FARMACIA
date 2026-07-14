import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TipoDecisaoEnum, pg_enum


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agentes_ia.id"), nullable=False
    )
    tipo_decisao: Mapped[TipoDecisaoEnum] = mapped_column(
        pg_enum(TipoDecisaoEnum, "tipo_decisao_enum"), nullable=False
    )
    entidade_afetada: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    principio_ativo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principios_ativos.id")
    )
    decisao_tomada: Mapped[str] = mapped_column(Text, nullable=False)
    dados_base: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    justificativa: Mapped[str | None] = mapped_column(Text)
    confianca: Mapped[float | None] = mapped_column(Numeric(3, 2))
    sessao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # LLM-08/QA-03: modelo REAL que executou (resolvido em config.py na hora
    # da chamada), nunca o campo decorativo agentes_ia.modelo_llm — e dados
    # de custo/latência, sem os quais não há como decidir infraestrutura.
    # Nulos em decisões que não vieram de uma chamada a LLM (ex.: sync
    # fail-closed, movimentação de estoque).
    modelo_llm: Mapped[str | None] = mapped_column(String(80))
    tokens_totais: Mapped[int | None] = mapped_column(Integer)
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
