import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import FormaFarmaceuticaEnum, TarjaEnum, UnidadeConcentracaoEnum, ViaAdministracaoEnum


def _nome_comercial_nao_vazio(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("nome_comercial não pode ficar vazio ou conter só espaços")
    return v


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
    # QA (fail-closed): sem default. Antes tinha default=TarjaEnum.isento —
    # se o cadastro manual omitisse o campo (bypass do form), o produto
    # nascia com a tarja MENOS restritiva, silenciosamente. O default do
    # banco (0004) e o do model (produto.py) também mudaram para 'vermelha'
    # como rede de segurança, mas a via normal (API) agora exige a escolha
    # explícita — nunca cai em nenhum dos dois defaults.
    tarja: TarjaEnum
    tipo_liberacao: str = "imediata"
    preco_tabela: Decimal
    # DEPRECADO (BUG-06): nenhuma tool financeira usa mais este campo pra
    # decisão — custo real é lotes.custo_unitario. Mantido só por
    # compatibilidade com relatórios/consultas existentes.
    custo_medio: Decimal | None = None
    ativo: bool = True


class ProdutoCreate(ProdutoBase):
    # QA: o backend nunca confia no frontend — HTML `required`/`select`
    # bloqueia a maior parte disso na UI, mas uma chamada direta à API
    # ainda passava por cima. Redeclarados aqui (não em ProdutoBase/
    # ProdutoRead) para nunca arriscar rejeitar a leitura de uma linha já
    # existente que porventura não satisfaça uma constraint nova.
    concentracao_valor: Decimal = Field(gt=0)
    quantidade_embalagem: int = Field(gt=0)
    preco_tabela: Decimal = Field(ge=0)

    _valida_nome_comercial = field_validator("nome_comercial")(_nome_comercial_nao_vazio)


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
    concentracao_valor: Decimal | None = Field(default=None, gt=0)
    concentracao_unidade: UnidadeConcentracaoEnum | None = None
    quantidade_embalagem: int | None = Field(default=None, gt=0)
    tipo_liberacao: str | None = None
    preco_tabela: Decimal | None = Field(default=None, ge=0)
    custo_medio: Decimal | None = None
    ativo: bool | None = None

    _valida_nome_comercial = field_validator("nome_comercial")(_nome_comercial_nao_vazio)


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
