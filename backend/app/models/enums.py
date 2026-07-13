import enum

from sqlalchemy import Enum as SAEnum


class TarjaEnum(str, enum.Enum):
    isento = "isento"
    amarela = "amarela"
    vermelha = "vermelha"
    preta = "preta"


class FormaFarmaceuticaEnum(str, enum.Enum):
    comprimido = "comprimido"
    capsula = "capsula"
    xarope = "xarope"
    pomada = "pomada"
    gel = "gel"
    creme = "creme"
    solucao = "solucao"
    suspensao = "suspensao"
    injetavel = "injetavel"
    spray = "spray"
    adesivo = "adesivo"
    po = "po"
    supositorio = "supositorio"
    colirio = "colirio"


class ViaAdministracaoEnum(str, enum.Enum):
    oral = "oral"
    topica = "topica"
    injetavel = "injetavel"
    retal = "retal"
    oftalmica = "oftalmica"
    nasal = "nasal"
    inalatoria = "inalatoria"
    sublingual = "sublingual"
    otologica = "otologica"
    vaginal = "vaginal"


class UnidadeConcentracaoEnum(str, enum.Enum):
    mg = "mg"
    g = "g"
    ml = "ml"
    mcg = "mcg"
    ui = "ui"
    pct = "pct"


class StatusLoteEnum(str, enum.Enum):
    disponivel = "disponivel"
    reservado = "reservado"
    vencido = "vencido"
    bloqueado = "bloqueado"
    devolvido = "devolvido"


class CanalVendaEnum(str, enum.Enum):
    balcao = "balcao"
    avatar_ia = "avatar_ia"
    app = "app"
    delivery = "delivery"


class TipoAgenteEnum(str, enum.Enum):
    atendente = "atendente"
    gerente_estoque = "gerente_estoque"
    financeiro = "financeiro"
    orquestrador = "orquestrador"


class TipoDecisaoEnum(str, enum.Enum):
    sugestao_similar = "sugestao_similar"
    ajuste_preco = "ajuste_preco"
    alerta_estoque = "alerta_estoque"
    aprovacao_compra = "aprovacao_compra"
    bloqueio_venda = "bloqueio_venda"
    recomendacao_giro = "recomendacao_giro"
    resolucao_conflito = "resolucao_conflito"


class StatusAprovacaoEnum(str, enum.Enum):
    proposto = "proposto"
    aprovado = "aprovado"
    rejeitado = "rejeitado"
    auto_aprovado = "auto_aprovado"


def pg_enum(python_enum: type[enum.Enum], pg_name: str) -> SAEnum:
    # create_type=False: o tipo já existe no Postgres (migration 0002_enums.sql).
    # O SQLAlchemy nunca deve tentar criar/alterar esses tipos.
    return SAEnum(python_enum, name=pg_name, create_type=False, values_callable=lambda e: [m.value for m in e])
