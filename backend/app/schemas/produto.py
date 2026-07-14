import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FormaFarmaceuticaEnum, TarjaEnum, UnidadeConcentracaoEnum, ViaAdministracaoEnum


class ProdutoBase(BaseModel):
    principio_ativo_id: uuid.UUID | None = None
    fabricante_id: uuid.UUID
    nome_comercial: str
    codigo_barras: str | None = None
    registro_anvisa: str | None = None
    forma_farmaceutica: FormaFarmaceuticaEnum
    via_administracao: ViaAdministracaoEnum
    concentracao_valor: Decimal
    concentracao_unidade: UnidadeConcentracaoEnum
    quantidade_embalagem: int
    tarja: TarjaEnum = TarjaEnum.isento
    tipo_liberacao: str = "imediata"
    preco_tabela: Decimal
    # DEPRECADO (BUG-06): nenhuma tool financeira usa mais este campo pra
    # decisão — custo real é lotes.custo_unitario. Mantido só por
    # compatibilidade com relatórios/consultas existentes.
    custo_medio: Decimal | None = None
    ativo: bool = True


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    # SEC-06: "tarja" é deliberadamente EXCLUÍDA daqui. Rebaixar a tarja de um
    # produto por um PATCH genérico furava a RLS de 0012 (que só filtra por
    # tarja='isento') pela porta da frente. Alterar tarja agora exige o
    # endpoint privilegiado PATCH /produtos/{id}/tarja (auditado).
    principio_ativo_id: uuid.UUID | None = None
    fabricante_id: uuid.UUID | None = None
    nome_comercial: str | None = None
    codigo_barras: str | None = None
    registro_anvisa: str | None = None
    forma_farmaceutica: FormaFarmaceuticaEnum | None = None
    via_administracao: ViaAdministracaoEnum | None = None
    concentracao_valor: Decimal | None = None
    concentracao_unidade: UnidadeConcentracaoEnum | None = None
    quantidade_embalagem: int | None = None
    tipo_liberacao: str | None = None
    preco_tabela: Decimal | None = None
    custo_medio: Decimal | None = None
    ativo: bool | None = None


class ProdutoTarjaUpdate(BaseModel):
    """Endpoint privilegiado e auditado (PATCH /produtos/{id}/tarja) — a ÚNICA
    forma permitida de mudar a tarja de um produto já cadastrado."""

    tarja: TarjaEnum
    motivo: str = Field(min_length=10)


class ProdutoRead(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    id_externo: str | None = None
    origem: str
    sincronizado_em: datetime | None = None
