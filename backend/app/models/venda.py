import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import CanalVendaEnum, pg_enum


class Venda(Base):
    __tablename__ = "vendas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filial_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filiais.id", ondelete="RESTRICT"), nullable=False
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="SET NULL"))
    agente_atendimento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agentes_ia.id", ondelete="SET NULL")
    )
    canal: Mapped[CanalVendaEnum] = mapped_column(
        pg_enum(CanalVendaEnum, "canal_venda_enum"), nullable=False, default=CanalVendaEnum.balcao
    )
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    forma_pagamento: Mapped[str | None] = mapped_column(String(30))
    data_venda: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VendaItem(Base):
    __tablename__ = "vendas_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venda_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendas.id", ondelete="CASCADE"), nullable=False)
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    lote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="RESTRICT"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    desconto_aplicado: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    # subtotal é GENERATED ALWAYS no Postgres (migration 0007) — não mapeado, só lido.
