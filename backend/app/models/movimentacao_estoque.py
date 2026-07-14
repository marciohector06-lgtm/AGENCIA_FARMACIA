import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TipoMovimentacaoEnum, pg_enum


class MovimentacaoEstoque(Base):
    """Ledger append-only de mudanças em estoque.quantidade_atual (migration 0019).

    Única forma permitida de alterar quantidade: não existe UPDATE direto de
    quantidade_atual/quantidade_reservada pela API (fecha o SEC-11).
    """

    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (
        CheckConstraint("quantidade_delta <> 0", name="chk_delta_nao_zero"),
        CheckConstraint("quantidade_resultante >= 0", name="chk_resultante_nao_negativo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estoque_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[TipoMovimentacaoEnum] = mapped_column(
        pg_enum(TipoMovimentacaoEnum, "tipo_movimentacao_enum"), nullable=False
    )
    quantidade_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade_resultante: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    venda_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vendas.id", ondelete="SET NULL"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
