"""FASE 0: testes puros (sem banco) do MockAdapter e da regra de falha
fechada do sync worker. Cobrem o ERP hostil (F0-02) e a garantia de
idempotência/indisponibilidade de registrar_venda (F0-06/F0-07) sem precisar
de Postgres — por isso rodam sempre, sem TEST_DATABASE_URL.
"""

import pytest

from app.integrations.base import ERPIndisponivelError, ItemVendaParaERP, VendaParaERP
from app.integrations.mock_adapter import MockAdapter
from app.integrations.sync import _mapear_tarja


def test_tarja_ausente_e_falha_fechada() -> None:
    tarja, fail_closed = _mapear_tarja(None)
    assert tarja.value == "vermelha"
    assert fail_closed is True


def test_tarja_valor_nao_mapeavel_e_falha_fechada() -> None:
    tarja, fail_closed = _mapear_tarja("cod_legado_qualquer")
    assert tarja.value == "vermelha"
    assert fail_closed is True


@pytest.mark.parametrize("raw,esperado", [("isento", "isento"), (" Preta ", "preta"), ("AMARELA", "amarela")])
def test_tarja_valida_mapeia_corretamente_sem_falha_fechada(raw: str, esperado: str) -> None:
    tarja, fail_closed = _mapear_tarja(raw)
    assert tarja.value == esperado
    assert fail_closed is False


def test_mock_adapter_produto_com_tarja_ausente_esta_no_dataset() -> None:
    """Confirma que o dataset padrão do MockAdapter inclui o caso hostil (não é
    um modo especial) — regra F0-02: o ERP hostil é o comportamento normal."""
    adapter = MockAdapter()
    produtos = adapter.listar_produtos()
    tarjas_ausentes = [p for p in produtos if p.tarja_raw is None]
    tarjas_desconhecidas = [p for p in produtos if p.tarja_raw and _mapear_tarja(p.tarja_raw)[1]]
    assert len(tarjas_ausentes) >= 1
    assert len(tarjas_desconhecidas) >= 1


def test_mock_adapter_lote_sem_validade_esta_no_dataset() -> None:
    adapter = MockAdapter()
    lotes = adapter.listar_lotes()
    assert any(l.data_validade is None for l in lotes)


def _venda_exemplo(quantidade: int = 2) -> VendaParaERP:
    return VendaParaERP(
        filial_id_externa="FIL-001",
        itens=[ItemVendaParaERP(produto_id_externo="PROD-001", lote_id_externo="LOTE-001", quantidade=quantidade, preco_unitario="8.90")],
    )


def test_registrar_venda_idempotente_nao_debita_duas_vezes() -> None:
    adapter = MockAdapter()
    venda = _venda_exemplo(quantidade=5)

    r1 = adapter.registrar_venda(venda, idempotency_key="chave-fixa")
    r2 = adapter.registrar_venda(venda, idempotency_key="chave-fixa")

    assert r1.id_externo == r2.id_externo
    estoque = adapter.consultar_estoque("PROD-001", "LOTE-001", "FIL-001")
    assert estoque is not None
    assert estoque.quantidade_atual == 60 - 5  # debitou uma vez só


def test_registrar_venda_chave_diferente_debita_de_novo() -> None:
    adapter = MockAdapter()
    adapter.registrar_venda(_venda_exemplo(quantidade=5), idempotency_key="chave-1")
    adapter.registrar_venda(_venda_exemplo(quantidade=5), idempotency_key="chave-2")

    estoque = adapter.consultar_estoque("PROD-001", "LOTE-001", "FIL-001")
    assert estoque is not None
    assert estoque.quantidade_atual == 60 - 5 - 5


def test_registrar_venda_estoque_insuficiente_leva_a_erro() -> None:
    adapter = MockAdapter()
    with pytest.raises(ValueError):
        adapter.registrar_venda(_venda_exemplo(quantidade=9999), idempotency_key="qualquer")


@pytest.mark.parametrize(
    "chamada",
    [
        lambda a: a.listar_produtos(),
        lambda a: a.listar_lotes(),
        lambda a: a.listar_estoque(),
        lambda a: a.listar_filiais(),
        lambda a: a.consultar_estoque("PROD-001", "LOTE-001", "FIL-001"),
        lambda a: a.registrar_venda(_venda_exemplo(), idempotency_key="x"),
    ],
)
def test_modo_indisponivel_nunca_deixa_escrita_parcial(chamada) -> None:
    """F0-06/F0-07: ERP fora do ar precisa levantar ERPIndisponivelError em
    QUALQUER operação — quem chama é responsável por não escrever nada local
    quando isso acontece (nenhuma venda fantasma)."""
    adapter = MockAdapter(modo_falha="indisponivel")
    with pytest.raises(ERPIndisponivelError):
        chamada(adapter)


def test_modo_malformado_levanta_value_error_em_listagens() -> None:
    adapter = MockAdapter(modo_falha="malformado")
    with pytest.raises(ValueError):
        adapter.listar_produtos()
    with pytest.raises(ValueError):
        adapter.listar_lotes()
