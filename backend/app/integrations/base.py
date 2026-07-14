"""Camada anticorrupção entre o ERP de cada farmácia e o domínio deste sistema.

Regra da FASE 0: nenhuma tool de agente, nenhum endpoint de negócio, chama um
ERP diretamente. Tudo passa por um ERPAdapter, e o único jeito de trocar de
ERP é escrever um adaptador novo — nenhuma migration, tool ou agente muda.

Os DTOs abaixo são o "modelo canônico": todo adaptador (mock, linx, trier...)
deve devolver exatamente isto, não importa quão bagunçado seja o formato de
origem. Mas "canônico" não é "confiável" — nenhum campo aqui tem garantia de
integridade (um ERP real manda tarja com nome de campo trocado, custo nulo,
validade ausente). Quem decide o que fazer com um dado suspeito é o sync
worker (app/integrations/sync.py), nunca o adaptador e nunca os agentes.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class ProdutoExterno(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_externo: str
    nome_comercial: str
    # Bruto, de propósito: o adaptador não deve tentar validar/mapear a tarja
    # do ERP para o TarjaEnum — isso é regra de negócio clínica e pertence ao
    # sync worker (F0-03), que aplica a regra de falha fechada.
    tarja_raw: str | None = None
    principio_ativo_nome: str | None = None
    fabricante_nome: str | None = None
    forma_farmaceutica_raw: str | None = None
    via_administracao_raw: str | None = None
    concentracao_valor: Decimal | None = None
    concentracao_unidade_raw: str | None = None
    quantidade_embalagem: int | None = None
    codigo_barras: str | None = None
    registro_anvisa: str | None = None
    preco_tabela: Decimal | None = None
    custo_medio: Decimal | None = None
    ativo: bool = True


class LoteExterno(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_externo: str
    produto_id_externo: str
    numero_lote: str
    data_fabricacao: date | None = None
    data_validade: date | None = None
    quantidade_recebida: int | None = None
    custo_unitario: Decimal | None = None


class FilialExterna(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_externo: str
    nome: str
    cnpj: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    ativo: bool = True


class EstoqueExterno(BaseModel):
    """Posição de estoque por lote+filial.

    Usada tanto em listar_estoque (sync em lote, F0-04) quanto no retorno de
    consultar_estoque (checagem ao vivo, F0-06) — no segundo caso representa
    a posição *daquele* lote específico, não um agregado do produto inteiro,
    porque a venda sempre debita um lote (FEFO já decidiu qual antes de
    confirmar).
    """

    model_config = ConfigDict(extra="ignore")

    produto_id_externo: str
    lote_id_externo: str
    filial_id_externa: str
    quantidade_atual: int
    quantidade_reservada: int = 0


class ItemVendaParaERP(BaseModel):
    produto_id_externo: str
    lote_id_externo: str
    quantidade: int
    preco_unitario: Decimal


class VendaParaERP(BaseModel):
    filial_id_externa: str
    itens: list[ItemVendaParaERP]
    forma_pagamento: str = "cartao"
    cliente_documento: str | None = None


class VendaConfirmadaERP(BaseModel):
    id_externo: str
    confirmado_em: datetime


class ERPIndisponivelError(RuntimeError):
    """O ERP não respondeu (timeout, 5xx, conexão recusada, retorno ilegível).

    Regra F0-06: isto nunca pode virar uma venda gravada no espelho local —
    quem chama registrar_venda precisa tratar esta exceção explicitamente e
    abortar toda a confirmação, sem escrita parcial.
    """


class ERPAdapter(Protocol):
    """Contrato mínimo que qualquer ERP precisa cumprir.

    listar_filiais/listar_estoque não estavam no esboço original do
    documento de correção (que listava só listar_produtos, listar_lotes,
    consultar_estoque e registrar_venda) — foram adicionados porque o sync
    worker (F0-03/F0-04) precisa de alguma fonte em lote para popular
    filiais e a tabela estoque local, e não faria sentido inventar isso via
    N chamadas de consultar_estoque por produto.
    """

    def listar_filiais(self, desde: datetime | None = None) -> list[FilialExterna]: ...

    def listar_produtos(self, desde: datetime | None = None) -> list[ProdutoExterno]: ...

    def listar_lotes(self, desde: datetime | None = None) -> list[LoteExterno]: ...

    def listar_estoque(self, desde: datetime | None = None) -> list[EstoqueExterno]: ...

    def consultar_estoque(self, produto_id_externo: str, lote_id_externo: str, filial_id_externa: str) -> EstoqueExterno | None: ...

    def registrar_venda(self, venda: VendaParaERP, idempotency_key: str) -> VendaConfirmadaERP: ...

    def consultar_venda_por_idempotency_key(self, idempotency_key: str) -> VendaConfirmadaERP | None:
        """Base do reconciliador (F0-06/outbox): pergunta ao ERP "essa venda
        entrou?" sem tentar registrar de novo. Retorna None se o ERP nunca
        recebeu essa idempotency_key — nesse caso a venda pendente vira 'falha'
        localmente, nunca 'confirmada' por omissão."""
        ...
