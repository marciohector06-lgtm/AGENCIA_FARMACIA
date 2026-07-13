import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import StatusAprovacaoEnum, pg_enum


class PrecificacaoHistorico(Base):
    __tablename__ = "precificacao_historico"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="SET NULL"))
    preco_anterior: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preco_novo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # percentual_desconto é GENERATED ALWAYS no Postgres (migration 0006) — não mapeado, só lido.
    margem_resultante: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    proposto_por_agente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agentes_ia.id"), nullable=False
    )
    aprovado_por_agente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agentes_ia.id"))
    status_aprovacao: Mapped[StatusAprovacaoEnum] = mapped_column(
        pg_enum(StatusAprovacaoEnum, "status_aprovacao_enum"), nullable=False, default=StatusAprovacaoEnum.proposto
    )
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
