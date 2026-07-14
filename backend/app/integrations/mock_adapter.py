"""ERP fictício usado como ambiente de simulação (F0-02).

Não é só um gerador de dados de teste: este é o "ERP hostil" que o
MockAdapter deliberadamente simula, porque um ERP real é hostil — campo de
tarja ausente ou com nome trocado, produto sem custo, lote sem validade,
API que cai. Se o sistema não sobrevive a este adaptador mal-comportado, não
sobrevive a uma farmácia real. Os casos hostis abaixo são permanentes (fazem
parte do dataset padrão, não um modo especial) — só a indisponibilidade total
do "ERP" e o payload malformado são opt-in via `modo_falha`, porque esses dois
description precisam ser exercícios isolados nos testes (F0-06/F0-07).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from app.integrations.base import (
    ERPIndisponivelError,
    EstoqueExterno,
    FilialExterna,
    LoteExterno,
    ProdutoExterno,
    VendaConfirmadaERP,
    VendaParaERP,
)

ModoFalha = Literal["normal", "indisponivel", "malformado"]


class _EstoqueInterno:
    """Estado mutável da posição de estoque, para poder debitar em registrar_venda."""

    def __init__(self, produto_id_externo: str, lote_id_externo: str, filial_id_externa: str, quantidade_atual: int) -> None:
        self.produto_id_externo = produto_id_externo
        self.lote_id_externo = lote_id_externo
        self.filial_id_externa = filial_id_externa
        self.quantidade_atual = quantidade_atual
        self.quantidade_reservada = 0


class MockAdapter:
    """Implementa ERPAdapter (Protocol) com dados sintéticos e falhas hostis."""

    def __init__(self, modo_falha: ModoFalha = "normal") -> None:
        self.modo_falha = modo_falha
        self._vendas_confirmadas: dict[str, VendaConfirmadaERP] = {}
        self._seed()

    def _seed(self) -> None:
        hoje = date.today()

        self._filiais = [
            FilialExterna(id_externo="FIL-001", nome="Filial Mock Centro", cnpj="11.111.111/0001-11", cidade="São Paulo", uf="SP"),
        ]

        # --- Produtos: mix de MIP normal, controlado real e casos hostis. ---
        self._produtos = [
            ProdutoExterno(
                id_externo="PROD-001", nome_comercial="Dorexin 750mg", tarja_raw="isento",
                principio_ativo_nome="Paracetamol", fabricante_nome="Fábrica Fictícia LTDA",
                forma_farmaceutica_raw="comprimido", via_administracao_raw="oral",
                concentracao_valor=Decimal("750"), concentracao_unidade_raw="mg",
                quantidade_embalagem=20, preco_tabela=Decimal("8.90"), custo_medio=Decimal("3.50"),
            ),
            ProdutoExterno(
                id_externo="PROD-002", nome_comercial="Inflacil 400mg", tarja_raw="isento",
                principio_ativo_nome="Ibuprofeno", fabricante_nome="Fábrica Fictícia LTDA",
                forma_farmaceutica_raw="comprimido", via_administracao_raw="oral",
                concentracao_valor=Decimal("400"), concentracao_unidade_raw="mg",
                quantidade_embalagem=20, preco_tabela=Decimal("11.50"), custo_medio=Decimal("4.20"),
            ),
            # HOSTIL: campo de tarja ausente no ERP (o adaptador não sabe a tarja —
            # muitos ERPs de balcão simplesmente não têm essa coluna preenchida).
            ProdutoExterno(
                id_externo="PROD-003", nome_comercial="Algivex", tarja_raw=None,
                principio_ativo_nome="Dipirona", fabricante_nome="Genéricos União SA",
                forma_farmaceutica_raw="comprimido", via_administracao_raw="oral",
                concentracao_valor=Decimal("500"), concentracao_unidade_raw="mg",
                quantidade_embalagem=10, preco_tabela=Decimal("6.50"), custo_medio=Decimal("2.10"),
            ),
            # HOSTIL: tarja vem num código legado do ERP que não mapeamos.
            ProdutoExterno(
                id_externo="PROD-004", nome_comercial="Bactrizen 500", tarja_raw="cod_legado_7",
                principio_ativo_nome="Amoxicilina", fabricante_nome="Genéricos União SA",
                forma_farmaceutica_raw="capsula", via_administracao_raw="oral",
                concentracao_valor=Decimal("500"), concentracao_unidade_raw="mg",
                quantidade_embalagem=15, preco_tabela=Decimal("22.90"), custo_medio=Decimal("9.80"),
            ),
            # Controlado real (tarja preta) — controle negativo: precisa continuar
            # invisível ao atendente independentemente de ser hostil ou não.
            ProdutoExterno(
                id_externo="PROD-005", nome_comercial="Clonazan 2mg", tarja_raw="preta",
                principio_ativo_nome="Clonazepam", fabricante_nome="Fábrica Fictícia LTDA",
                forma_farmaceutica_raw="comprimido", via_administracao_raw="oral",
                concentracao_valor=Decimal("2"), concentracao_unidade_raw="mg",
                quantidade_embalagem=30, preco_tabela=Decimal("18.00"), custo_medio=Decimal("7.00"),
            ),
            # HOSTIL: produto sem custo cadastrado no ERP.
            ProdutoExterno(
                id_externo="PROD-006", nome_comercial="Vitaflex C", tarja_raw="isento",
                principio_ativo_nome=None, fabricante_nome="Fábrica Fictícia LTDA",
                forma_farmaceutica_raw="comprimido", via_administracao_raw="oral",
                concentracao_valor=Decimal("1000"), concentracao_unidade_raw="mg",
                quantidade_embalagem=10, preco_tabela=Decimal("15.00"), custo_medio=None,
            ),
        ]

        # --- Lotes: válidos, vencido e um hostil (sem data de validade). ---
        self._lotes = [
            LoteExterno(
                id_externo="LOTE-001", produto_id_externo="PROD-001", numero_lote="A1",
                data_fabricacao=hoje - timedelta(days=200), data_validade=hoje + timedelta(days=400),
                quantidade_recebida=100, custo_unitario=Decimal("3.50"),
            ),
            # Lote JÁ VENCIDO — precisa ser rejeitado pelo FEFO/RLS a jusante (Fase 2);
            # aqui só garantimos que o espelho reflete a validade real.
            LoteExterno(
                id_externo="LOTE-002", produto_id_externo="PROD-002", numero_lote="B7",
                data_fabricacao=hoje - timedelta(days=800), data_validade=hoje - timedelta(days=10),
                quantidade_recebida=50, custo_unitario=Decimal("4.20"),
            ),
            LoteExterno(
                id_externo="LOTE-003", produto_id_externo="PROD-003", numero_lote="C3",
                data_fabricacao=hoje - timedelta(days=100), data_validade=hoje + timedelta(days=300),
                quantidade_recebida=80, custo_unitario=Decimal("2.10"),
            ),
            LoteExterno(
                id_externo="LOTE-004", produto_id_externo="PROD-004", numero_lote="D9",
                data_fabricacao=hoje - timedelta(days=50), data_validade=hoje + timedelta(days=500),
                quantidade_recebida=40, custo_unitario=Decimal("9.80"),
            ),
            LoteExterno(
                id_externo="LOTE-005", produto_id_externo="PROD-005", numero_lote="E2",
                data_fabricacao=hoje - timedelta(days=30), data_validade=hoje + timedelta(days=600),
                quantidade_recebida=20, custo_unitario=Decimal("7.00"),
            ),
            # HOSTIL: lote sem data de validade — falha fechada também aqui (a
            # regra clínica não pode assumir "nunca vence").
            LoteExterno(
                id_externo="LOTE-006", produto_id_externo="PROD-006", numero_lote="F4",
                data_fabricacao=hoje - timedelta(days=10), data_validade=None,
                quantidade_recebida=60, custo_unitario=None,
            ),
        ]

        self._estoque = [
            _EstoqueInterno("PROD-001", "LOTE-001", "FIL-001", 60),
            _EstoqueInterno("PROD-002", "LOTE-002", "FIL-001", 15),
            _EstoqueInterno("PROD-003", "LOTE-003", "FIL-001", 40),
            _EstoqueInterno("PROD-004", "LOTE-004", "FIL-001", 25),
            _EstoqueInterno("PROD-005", "LOTE-005", "FIL-001", 10),
            _EstoqueInterno("PROD-006", "LOTE-006", "FIL-001", 30),
        ]

    def _checar_disponibilidade(self) -> None:
        if self.modo_falha == "indisponivel":
            raise ERPIndisponivelError(
                "MockAdapter em modo 'indisponivel': simula timeout/erro 5xx/conexão recusada do ERP."
            )

    def listar_filiais(self, desde: datetime | None = None) -> list[FilialExterna]:
        self._checar_disponibilidade()
        return list(self._filiais)

    def listar_produtos(self, desde: datetime | None = None) -> list[ProdutoExterno]:
        self._checar_disponibilidade()
        if self.modo_falha == "malformado":
            raise ValueError("Payload do ERP não pôde ser interpretado (simulação de resposta malformada).")
        return list(self._produtos)

    def listar_lotes(self, desde: datetime | None = None) -> list[LoteExterno]:
        self._checar_disponibilidade()
        if self.modo_falha == "malformado":
            raise ValueError("Payload do ERP não pôde ser interpretado (simulação de resposta malformada).")
        return list(self._lotes)

    def listar_estoque(self, desde: datetime | None = None) -> list[EstoqueExterno]:
        self._checar_disponibilidade()
        return [
            EstoqueExterno(
                produto_id_externo=e.produto_id_externo,
                lote_id_externo=e.lote_id_externo,
                filial_id_externa=e.filial_id_externa,
                quantidade_atual=e.quantidade_atual,
                quantidade_reservada=e.quantidade_reservada,
            )
            for e in self._estoque
        ]

    def consultar_estoque(self, produto_id_externo: str, lote_id_externo: str, filial_id_externa: str) -> EstoqueExterno | None:
        self._checar_disponibilidade()
        for e in self._estoque:
            if (
                e.produto_id_externo == produto_id_externo
                and e.lote_id_externo == lote_id_externo
                and e.filial_id_externa == filial_id_externa
            ):
                return EstoqueExterno(
                    produto_id_externo=e.produto_id_externo,
                    lote_id_externo=e.lote_id_externo,
                    filial_id_externa=e.filial_id_externa,
                    quantidade_atual=e.quantidade_atual,
                    quantidade_reservada=e.quantidade_reservada,
                )
        return None

    def registrar_venda(self, venda: VendaParaERP, idempotency_key: str) -> VendaConfirmadaERP:
        self._checar_disponibilidade()

        # Idempotência: mesma chave nunca debita o estoque simulado duas vezes.
        if idempotency_key in self._vendas_confirmadas:
            return self._vendas_confirmadas[idempotency_key]

        linhas_afetadas: list[_EstoqueInterno] = []
        for item in venda.itens:
            linha = next(
                (
                    e
                    for e in self._estoque
                    if e.produto_id_externo == item.produto_id_externo
                    and e.lote_id_externo == item.lote_id_externo
                    and e.filial_id_externa == venda.filial_id_externa
                ),
                None,
            )
            disponivel = (linha.quantidade_atual - linha.quantidade_reservada) if linha else 0
            if linha is None or disponivel < item.quantidade:
                raise ValueError(
                    f"Estoque insuficiente no ERP para lote_id_externo={item.lote_id_externo} "
                    f"(disponível={disponivel}, solicitado={item.quantidade})"
                )
            linhas_afetadas.append(linha)

        for linha, item in zip(linhas_afetadas, venda.itens, strict=True):
            linha.quantidade_atual -= item.quantidade

        resultado = VendaConfirmadaERP(
            id_externo=f"mock-venda-{uuid.uuid4().hex[:12]}",
            confirmado_em=datetime.now(timezone.utc),
        )
        self._vendas_confirmadas[idempotency_key] = resultado
        return resultado

    def consultar_venda_por_idempotency_key(self, idempotency_key: str) -> VendaConfirmadaERP | None:
        self._checar_disponibilidade()
        return self._vendas_confirmadas.get(idempotency_key)
