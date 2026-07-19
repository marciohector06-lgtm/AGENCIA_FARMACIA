import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import (
    FormaFarmaceuticaEnum,
    TarjaEnum,
    UnidadeConcentracaoEnum,
    ViaAdministracaoEnum,
    pg_enum,
)
from app.models.mixins import OrigemErpMixin, TimestampMixin


class Produto(OrigemErpMixin, TimestampMixin, Base):
    __tablename__ = "produtos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principio_ativo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("principios_ativos.id", ondelete="RESTRICT")
    )
    fabricante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fabricantes.id", ondelete="RESTRICT"), nullable=False
    )
    nome_comercial: Mapped[str] = mapped_column(String(150), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(14), unique=True)
    registro_anvisa: Mapped[str | None] = mapped_column(String(30))
    # Agente Tributário (migration 0005): usado por IdentificarProdutosTool
    # para casar item de NF-e -> produto cadastrado. Nullable — cadastro
    # existente não tem esse dado retroativamente.
    ncm: Mapped[str | None] = mapped_column(String(10))
    forma_farmaceutica: Mapped[FormaFarmaceuticaEnum] = mapped_column(
        pg_enum(FormaFarmaceuticaEnum, "forma_farmaceutica_enum"), nullable=False
    )
    via_administracao: Mapped[ViaAdministracaoEnum] = mapped_column(
        pg_enum(ViaAdministracaoEnum, "via_administracao_enum"), nullable=False
    )
    concentracao_valor: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    concentracao_unidade: Mapped[UnidadeConcentracaoEnum] = mapped_column(
        pg_enum(UnidadeConcentracaoEnum, "unidade_concentracao_enum"), nullable=False
    )
    quantidade_embalagem: Mapped[int] = mapped_column(Integer, nullable=False)
    # QA (fail-closed): default 'vermelha', não 'isento' — mesma regra do
    # sync (app/integrations/sync.py::_mapear_tarja): se tarja não foi
    # definida explicitamente por algum caminho, assume o mais restritivo,
    # nunca o menos. ProdutoCreate exige tarja explicitamente, então este
    # default é só rede de segurança (nunca deveria ser acionado via API).
    tarja: Mapped[TarjaEnum] = mapped_column(
        pg_enum(TarjaEnum, "tarja_enum"), nullable=False, default=TarjaEnum.vermelha
    )
    # exige_prescricao é GENERATED ALWAYS AS (tarja <> 'isento') STORED no Postgres
    # (migration 0005) e é intencionalmente omitida deste mapeamento: o banco é
    # a fonte da verdade, a API não deve tentar escrever nela.
    tipo_liberacao: Mapped[str] = mapped_column(String(30), nullable=False, default="imediata")
    preco_tabela: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # DEPRECADO (BUG-06): nunca mantido em dia (nada no projeto faz UPDATE
    # nele) e nenhuma tool financeira lê mais daqui — o custo real de venda é
    # lotes.custo_unitario (por lote, vindo do ERP via sync). Mantido só pra
    # não quebrar relatórios/consultas existentes que ainda apontem pra cá;
    # não usar em nenhuma decisão financeira nova.
    custo_medio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
