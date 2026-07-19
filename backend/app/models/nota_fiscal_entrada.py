import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import StatusItemNfeEnum, StatusNfeEntradaEnum, pg_enum


class NotaFiscalEntrada(Base):
    """Agente Tributário (Bloco 1): NF-e recebida por email, aguardando
    confirmação humana. Nunca escrita por app_backend fora do endpoint de
    confirmação (POST /notas-entrada/{id}/confirmar) — quem grava a linha
    inicial ('aguardando_confirmacao') é sempre a role agente_tributario."""

    __tablename__ = "notas_fiscais_entrada"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filial_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("filiais.id"), nullable=False)
    chave_acesso: Mapped[str] = mapped_column(String(44), nullable=False, unique=True)
    numero_nota: Mapped[str] = mapped_column(String(20), nullable=False)
    serie: Mapped[str] = mapped_column(String(5), nullable=False)
    cnpj_emitente: Mapped[str] = mapped_column(String(18), nullable=False)
    nome_emitente: Mapped[str] = mapped_column(String(150), nullable=False)
    data_emissao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    xml_raw: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[StatusNfeEntradaEnum] = mapped_column(
        pg_enum(StatusNfeEntradaEnum, "status_nfe_entrada_enum"),
        nullable=False,
        default=StatusNfeEntradaEnum.aguardando_confirmacao,
    )
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_por_operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operadores.id")
    )


class NotaFiscalEntradaItem(Base):
    __tablename__ = "notas_fiscais_entrada_itens"
    __table_args__ = (CheckConstraint("quantidade > 0", name="chk_notas_fiscais_entrada_itens_quantidade_positiva"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nota_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notas_fiscais_entrada.id", ondelete="CASCADE"), nullable=False
    )
    # NULL se o produto não foi encontrado no cadastro (NCM ou nome não bate).
    produto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("produtos.id"))
    ncm: Mapped[str] = mapped_column(String(10), nullable=False)
    descricao_produto: Mapped[str] = mapped_column(String(200), nullable=False)
    numero_lote: Mapped[str | None] = mapped_column(String(40))
    data_validade: Mapped[date | None] = mapped_column(Date)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    valor_total_item: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    v_icms_st: Mapped[Decimal] = mapped_column("v_icms_st", Numeric(10, 2), nullable=False, default=0)
    p_pis: Mapped[Decimal] = mapped_column("p_pis", Numeric(6, 4), nullable=False, default=0)
    v_pis: Mapped[Decimal] = mapped_column("v_pis", Numeric(10, 2), nullable=False, default=0)
    p_cofins: Mapped[Decimal] = mapped_column("p_cofins", Numeric(6, 4), nullable=False, default=0)
    v_cofins: Mapped[Decimal] = mapped_column("v_cofins", Numeric(10, 2), nullable=False, default=0)
    # Preenchido só pelo endpoint de confirmação (app_backend) — nunca pelo agente.
    lote_criado_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lotes.id"))
    status_produto: Mapped[StatusItemNfeEnum] = mapped_column(
        pg_enum(StatusItemNfeEnum, "status_item_nfe_enum"), nullable=False, default=StatusItemNfeEnum.identificado
    )
