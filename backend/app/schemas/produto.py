import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

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
    custo_medio: Decimal | None = None
    ativo: bool = True


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
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
    tarja: TarjaEnum | None = None
    tipo_liberacao: str | None = None
    preco_tabela: Decimal | None = None
    custo_medio: Decimal | None = None
    ativo: bool | None = None


class ProdutoRead(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
