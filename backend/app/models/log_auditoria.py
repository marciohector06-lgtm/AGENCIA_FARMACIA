import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
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
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
