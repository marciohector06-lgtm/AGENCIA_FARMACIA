"""FASE 3 (integridade de negócio). Mesma infraestrutura das fases anteriores
— precisa de TEST_DATABASE_URL + migrations 0001-00xx aplicadas e credenciais
de agente configuradas.
"""

import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.integrations.sync import _backend_session

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


def _criar_produto_manual(*, custo_medio: str | None, preco_tabela: str = "9.90") -> uuid.UUID:
    session = _backend_session()
    try:
        fabricante_id = session.execute(
            text("INSERT INTO fabricantes (nome) VALUES (:n) RETURNING id"),
            {"n": f"Fabricante F3 {uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        produto_id = session.execute(
            text(
                """
                INSERT INTO produtos (fabricante_id, nome_comercial, forma_farmaceutica, via_administracao,
                    concentracao_valor, concentracao_unidade, quantidade_embalagem, tarja, preco_tabela, custo_medio)
                VALUES (:f, :n, 'pomada', 'topica', 10, 'mg', 1, 'isento', :preco, :custo)
                RETURNING id
                """
            ),
            {
                "f": str(fabricante_id),
                "n": f"Produto F3 {uuid.uuid4().hex[:8]}",
                "preco": preco_tabela,
                "custo": custo_medio,
            },
        ).scalar_one()
        session.commit()
    finally:
        session.close()
    return produto_id


def _criar_lote_estoque(produto_id: uuid.UUID, *, custo_unitario: str | None, quantidade: int = 50) -> dict:
    session = _backend_session()
    try:
        lote_id = session.execute(
            text(
                """
                INSERT INTO lotes (produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
                VALUES (:p, :n, :fab, :val, :qtd, :custo, 'disponivel') RETURNING id
                """
            ),
            {
                "p": str(produto_id),
                "n": f"L{uuid.uuid4().hex[:8]}",
                "fab": date.today() - timedelta(days=100),
                "val": date.today() + timedelta(days=300),
                "qtd": quantidade,
                "custo": custo_unitario,
            },
        ).scalar_one()
        filial_id = session.execute(
            text("INSERT INTO filiais (nome) VALUES (:n) RETURNING id"), {"n": f"Filial F3 {uuid.uuid4().hex[:8]}"}
        ).scalar_one()
        estoque_id = session.execute(
            text("INSERT INTO estoque (filial_id, lote_id, quantidade_atual, quantidade_reservada) VALUES (:f, :l, :q, 0) RETURNING id"),
            {"f": str(filial_id), "l": str(lote_id), "q": quantidade},
        ).scalar_one()
        session.commit()
    finally:
        session.close()
    return {"lote_id": lote_id, "filial_id": filial_id, "estoque_id": estoque_id}


# ---------------------------------------------------------------------------
# BUG-05 / BUG-08 / BUG-08b: Decimal fim a fim + clamp + NUMERIC(7,2)
# ---------------------------------------------------------------------------


@requires_db
def test_calcular_margem_tool_usa_decimal_sem_erro_de_ponto_flutuante() -> None:
    from app.agents.tools.financeiro_tools import CalcularMargemTool

    # custo_medio do produto propositalmente diferente do custo_unitario do
    # lote — a tool (BUG-06) tem que usar o do lote, não o do produto.
    produto_id = _criar_produto_manual(custo_medio="999.99")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="10.10")
    tool = CalcularMargemTool()
    resultado = tool._run(lote_id=str(cenario["lote_id"]), preco_proposto=10.30)

    # (10.30 - 10.10) / 10.30 * 100 = 1.941747... -> 1.94 arredondado.
    # Em float puro, 10.30 - 10.10 já não bate exatamente com 0.2 por causa de
    # representação binária — é exatamente esse tipo de erro que Decimal evita.
    assert resultado["margem_percentual"] == 1.94


@requires_db
def test_aprovar_desconto_com_margem_extrema_nao_estoura_numeric() -> None:
    """BUG-05: preço de liquidação bem abaixo do custo (padrão 'lote perto do
    vencimento' que o backstory do CFO instrui a aceitar) não pode quebrar o
    INSERT com numeric field overflow."""
    from app.agents.registry import agente_id_for
    from app.agents.tools.financeiro_tools import AprovarOuRejeitarDescontoTool
    from app.models.precificacao_historico import PrecificacaoHistorico

    produto_id = _criar_produto_manual(custo_medio="30.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="30.00")

    with agent_session(AgentRole.GERENTE_ESTOQUE) as session:
        proposta = PrecificacaoHistorico(
            produto_id=produto_id,
            lote_id=cenario["lote_id"],
            preco_anterior=Decimal("30.00"),
            preco_novo=Decimal("2.00"),
            motivo="Teste de margem extrema",
            proposto_por_agente_id=agente_id_for(AgentRole.GERENTE_ESTOQUE),
        )
        session.add(proposta)
        session.flush()
        precificacao_id = proposta.id

    tool = AprovarOuRejeitarDescontoTool()
    resultado = tool._run(precificacao_id=str(precificacao_id), aprovar=True, justificativa="Liquidação de lote perto do vencimento")

    assert "erro" not in resultado
    # (2 - 30) / 2 * 100 = -1400.00, dentro do clamp de -9999.99 -> não precisa clampar aqui,
    # mas o ponto central é: isso não pode levantar numeric field overflow.
    assert resultado["margem_resultante"] == -1400.00

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        margem_no_banco = session.execute(
            text("SELECT margem_resultante FROM precificacao_historico WHERE id = :id"), {"id": str(precificacao_id)}
        ).scalar_one()
    assert margem_no_banco == Decimal("-1400.00")


@requires_db
def test_clamp_impede_margem_alem_do_limite_defensivo() -> None:
    from app.agents.registry import agente_id_for
    from app.agents.tools.financeiro_tools import AprovarOuRejeitarDescontoTool
    from app.models.precificacao_historico import PrecificacaoHistorico

    produto_id = _criar_produto_manual(custo_medio="100000.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="100000.00")

    with agent_session(AgentRole.GERENTE_ESTOQUE) as session:
        proposta = PrecificacaoHistorico(
            produto_id=produto_id,
            lote_id=cenario["lote_id"],
            preco_anterior=Decimal("100000.00"),
            preco_novo=Decimal("0.01"),
            motivo="Teste de clamp",
            proposto_por_agente_id=agente_id_for(AgentRole.GERENTE_ESTOQUE),
        )
        session.add(proposta)
        session.flush()
        precificacao_id = proposta.id

    tool = AprovarOuRejeitarDescontoTool()
    resultado = tool._run(precificacao_id=str(precificacao_id), aprovar=True, justificativa="Teste de clamp defensivo")

    # margem real seria ~-999999900%, clampada para -9999.99
    assert resultado["margem_resultante"] == -9999.99


# ---------------------------------------------------------------------------
# BUG-07: proposta duplicada
# ---------------------------------------------------------------------------


@requires_db
def test_registrar_proposta_duas_vezes_no_mesmo_lote_nao_duplica() -> None:
    from app.agents.tools.estoque_tools import RegistrarPropostaDescontoTool

    produto_id = _criar_produto_manual(custo_medio="5.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00")

    tool = RegistrarPropostaDescontoTool()
    primeira = tool._run(produto_id=str(produto_id), lote_id=str(cenario["lote_id"]), preco_novo=7.00, motivo="Primeira proposta de teste")
    segunda = tool._run(produto_id=str(produto_id), lote_id=str(cenario["lote_id"]), preco_novo=6.50, motivo="Segunda tentativa pro mesmo lote")

    assert primeira["precificacao_id"] == segunda["precificacao_id"]
    assert "aviso" in segunda

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        total = session.execute(
            text("SELECT count(*) FROM precificacao_historico WHERE lote_id = :id AND status_aprovacao = 'proposto'"),
            {"id": str(cenario["lote_id"])},
        ).scalar_one()
    assert total == 1


# ---------------------------------------------------------------------------
# BUG-01: preco_efetivo() é a única fonte de preço pra cobrança. Este é o
# GATE OBRIGATÓRIO da FASE 3 — tem que passar antes de qualquer coisa em BUG-06.
# ---------------------------------------------------------------------------


def _propor_e_aprovar_desconto(produto_id: uuid.UUID, lote_id: uuid.UUID | None, preco_novo: str, motivo: str = "Teste BUG-01") -> uuid.UUID:
    from app.agents.registry import agente_id_for
    from app.models.precificacao_historico import PrecificacaoHistorico

    with agent_session(AgentRole.GERENTE_ESTOQUE) as session:
        preco_atual = session.execute(text("SELECT preco_tabela FROM produtos WHERE id = :id"), {"id": str(produto_id)}).scalar_one()
        proposta = PrecificacaoHistorico(
            produto_id=produto_id,
            lote_id=lote_id,
            preco_anterior=preco_atual,
            preco_novo=Decimal(preco_novo),
            motivo=motivo,
            proposto_por_agente_id=agente_id_for(AgentRole.GERENTE_ESTOQUE),
        )
        session.add(proposta)
        session.flush()
        precificacao_id = proposta.id

    from app.agents.tools.financeiro_tools import AprovarOuRejeitarDescontoTool

    resultado = AprovarOuRejeitarDescontoTool()._run(precificacao_id=str(precificacao_id), aprovar=True, justificativa="Aprovado em teste")
    assert resultado["status_aprovacao"] == "aprovado", resultado
    return precificacao_id


@requires_db
def test_gate_preco_efetivo_usa_desconto_aprovado_do_lote_nao_preco_tabela() -> None:
    """GATE OBRIGATÓRIO: proposta criada -> aprovada -> preço efetivo do
    mesmo lote é o com desconto, não preco_tabela. Se isto falhar, a Fase 3
    para aqui — não seguimos pra BUG-06."""
    from app.agents.pricing import preco_efetivo

    produto_id = _criar_produto_manual(custo_medio="5.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00")

    # Antes de qualquer desconto: preço efetivo é a tabela.
    assert preco_efetivo(produto_id, cenario["lote_id"]) == Decimal("10.00")

    _propor_e_aprovar_desconto(produto_id, cenario["lote_id"], preco_novo="7.00")

    preco = preco_efetivo(produto_id, cenario["lote_id"])
    assert preco == Decimal("7.00"), f"esperado desconto de R$7.00, veio {preco} (BUG-01 não corrigido: ainda usando preco_tabela)"

    # E produtos.preco_tabela continua intocado — a aprovação NUNCA escreve lá (BUG-01).
    with agent_session(AgentRole.ORQUESTRADOR) as session:
        preco_tabela_no_banco = session.execute(text("SELECT preco_tabela FROM produtos WHERE id = :id"), {"id": str(produto_id)}).scalar_one()
    assert preco_tabela_no_banco == Decimal("10.00")


@requires_db
def test_gate_venda_item_grava_preco_com_desconto() -> None:
    """Mesmo gate, mas fechando o ciclo até a escrita real: _criar_venda_pendente
    usando o preço resolvido por preco_efetivo grava o desconto em vendas_itens,
    não preco_tabela."""
    from app.agents.pricing import preco_efetivo
    from app.agents.service import _criar_venda_pendente, _idempotency_key_venda
    from app.schemas.chat import ChatAtendimentoRequest

    produto_id = _criar_produto_manual(custo_medio="5.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00")
    _propor_e_aprovar_desconto(produto_id, cenario["lote_id"], preco_novo="6.50")

    preco = preco_efetivo(produto_id, cenario["lote_id"])
    assert preco == Decimal("6.50")

    sessao_id = uuid.uuid4()
    request = ChatAtendimentoRequest(
        filial_id=cenario["filial_id"], mensagem="x", produto_id=produto_id, lote_id=cenario["lote_id"], quantidade=3
    )
    idempotency_key = _idempotency_key_venda(sessao_id, produto_id, cenario["lote_id"], 3)
    valor_total = preco * 3
    venda_id = _criar_venda_pendente(request, cenario["lote_id"], preco, valor_total, idempotency_key, sessao_id)

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        preco_gravado, quantidade_gravada = session.execute(
            text("SELECT preco_unitario, quantidade FROM vendas_itens WHERE venda_id = :id"), {"id": str(venda_id)}
        ).first()
    assert preco_gravado == Decimal("6.50"), "vendas_itens.preco_unitario tem que ser o preço COM desconto, não preco_tabela"
    assert quantidade_gravada == 3

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        valor_total_gravado = session.execute(text("SELECT valor_total FROM vendas WHERE id = :id"), {"id": str(venda_id)}).scalar_one()
    assert valor_total_gravado == Decimal("19.50")  # 6.50 * 3, não 10.00 * 3


def _criar_proposta_ja_aprovada(produto_id: uuid.UUID, lote_id: uuid.UUID | None, preco_novo: str) -> None:
    """Insere uma proposta já 'aprovada' direto (sem passar por
    AprovarOuRejeitarDescontoTool) — usado só pra testar o cascade de
    preco_efetivo isoladamente. Desconto geral de produto (lote_id=None) não
    tem lote pra checar custo, então AprovarOuRejeitarDescontoTool (BUG-06)
    recusa aprovar por "custo indisponível" de propósito — o schema ainda
    suporta esse caso (é o tier 2 do cascade), só não há hoje nenhuma tool
    que o produza de ponta a ponta. Via app_backend porque a RLS de
    agente_estoque só permite INSERT com status_aprovacao='proposto'
    (0012::ins_gerente_propoe) — correto, é só o teste que precisa contornar."""
    from app.agents.registry import agente_id_for

    session = _backend_session()
    try:
        preco_atual = session.execute(text("SELECT preco_tabela FROM produtos WHERE id = :id"), {"id": str(produto_id)}).scalar_one()
        session.execute(
            text(
                """
                INSERT INTO precificacao_historico
                    (produto_id, lote_id, preco_anterior, preco_novo, motivo, proposto_por_agente_id,
                     status_aprovacao, aprovado_por_agente_id, aprovado_em)
                VALUES (:produto_id, :lote_id, :preco_anterior, :preco_novo, :motivo, :proposto_por,
                        'aprovado', :aprovado_por, :aprovado_em)
                """
            ),
            {
                "produto_id": str(produto_id),
                "lote_id": str(lote_id) if lote_id else None,
                "preco_anterior": preco_atual,
                "preco_novo": Decimal(preco_novo),
                "motivo": "Proposta inserida já aprovada (teste de cascade)",
                "proposto_por": str(agente_id_for(AgentRole.GERENTE_ESTOQUE)),
                "aprovado_por": str(agente_id_for(AgentRole.FINANCEIRO)),
                "aprovado_em": datetime.now(timezone.utc),
            },
        )
        session.commit()
    finally:
        session.close()


@requires_db
def test_preco_efetivo_prioriza_desconto_do_lote_sobre_desconto_do_produto() -> None:
    from app.agents.pricing import preco_efetivo

    produto_id = _criar_produto_manual(custo_medio="5.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00")

    _criar_proposta_ja_aprovada(produto_id, None, preco_novo="8.00")
    assert preco_efetivo(produto_id, cenario["lote_id"]) == Decimal("8.00")

    _propor_e_aprovar_desconto(produto_id, cenario["lote_id"], preco_novo="6.00", motivo="Desconto específico do lote")
    assert preco_efetivo(produto_id, cenario["lote_id"]) == Decimal("6.00"), "desconto do lote tem que ganhar do desconto geral do produto"


# ---------------------------------------------------------------------------
# BUG-06: custo vem do lote (ERP), nunca de produtos.custo_medio
# ---------------------------------------------------------------------------


@requires_db
def test_calcular_margem_usa_custo_do_lote_nao_custo_medio_do_produto() -> None:
    from app.agents.tools.financeiro_tools import CalcularMargemTool

    # custo_medio do produto deliberadamente diferente do custo_unitario do
    # lote — se a tool ainda lesse produtos.custo_medio, a margem bateria
    # com o valor errado (100.00), não com o do lote (5.00).
    produto_id = _criar_produto_manual(custo_medio="100.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00")

    resultado = CalcularMargemTool()._run(lote_id=str(cenario["lote_id"]), preco_proposto=10.00)
    assert resultado["custo_unitario"] == 5.00
    assert resultado["margem_percentual"] == 50.00  # (10-5)/10*100, não (10-100)/10*100


@requires_db
def test_calcular_margem_com_custo_zero_retorna_erro_custo_indisponivel() -> None:
    from app.agents.tools.financeiro_tools import CalcularMargemTool

    produto_id = _criar_produto_manual(custo_medio="10.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="0.00")

    resultado = CalcularMargemTool()._run(lote_id=str(cenario["lote_id"]), preco_proposto=8.00)
    assert resultado == {
        "erro": "custo_indisponivel",
        "aviso": "Lote sem custo cadastrado (NULL ou zero) — não aprove; recomende revisão manual.",
    }


@requires_db
def test_aprovar_desconto_com_custo_zero_forca_rejeicao_mesmo_pedindo_aprovar() -> None:
    """BUG-06: nunca aprovação no escuro — mesmo que o (suposto) LLM peça
    aprovar=True, a ferramenta recusa deterministicamente quando o custo do
    lote está indisponível."""
    from app.agents.registry import agente_id_for
    from app.agents.tools.financeiro_tools import AprovarOuRejeitarDescontoTool
    from app.models.precificacao_historico import PrecificacaoHistorico

    produto_id = _criar_produto_manual(custo_medio="10.00", preco_tabela="10.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="0.00")

    with agent_session(AgentRole.GERENTE_ESTOQUE) as session:
        proposta = PrecificacaoHistorico(
            produto_id=produto_id,
            lote_id=cenario["lote_id"],
            preco_anterior=Decimal("10.00"),
            preco_novo=Decimal("8.00"),
            motivo="Teste custo indisponível",
            proposto_por_agente_id=agente_id_for(AgentRole.GERENTE_ESTOQUE),
        )
        session.add(proposta)
        session.flush()
        precificacao_id = proposta.id

    resultado = AprovarOuRejeitarDescontoTool()._run(
        precificacao_id=str(precificacao_id), aprovar=True, justificativa="Tentando aprovar sem custo disponível"
    )
    assert resultado["status_aprovacao"] == "rejeitado"
    assert resultado["erro"] == "custo_indisponivel"
    assert resultado["margem_resultante"] is None

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        status_no_banco = session.execute(
            text("SELECT status_aprovacao FROM precificacao_historico WHERE id = :id"), {"id": str(precificacao_id)}
        ).scalar_one()
    assert status_no_banco == "rejeitado"


# ---------------------------------------------------------------------------
# BUG-02 / BUG-03 / BUG-04: sem reserva prévia — revalidação atômica na
# confirmação é a única defesa contra concorrência (decisão da FASE 0,
# reafirmada em _run_atendimento_confirmacao). Duas "confirmações"
# simultâneas do mesmo lote com 1 unidade: uma sucede, a outra falha limpo.
# ---------------------------------------------------------------------------


@requires_db
def test_duas_confirmacoes_simultaneas_do_mesmo_lote_uma_sucede_outra_falha_limpo() -> None:
    import threading

    from app.agents.service import _debitar_estoque_venda

    produto_id = _criar_produto_manual(custo_medio="5.00")
    cenario = _criar_lote_estoque(produto_id, custo_unitario="5.00", quantidade=1)

    resultados: list[str] = []
    erros_inesperados: list[BaseException] = []

    def confirmar() -> None:
        try:
            _debitar_estoque_venda(cenario["estoque_id"], 1, None, "confirmação concorrente (teste BUG-04)", exigir_disponibilidade=True)
            resultados.append("sucesso")
        except ValueError:
            resultados.append("falhou_limpo")
        except Exception as exc:  # nunca deveria cair aqui — seria o 500 do CHECK
            erros_inesperados.append(exc)

    t1 = threading.Thread(target=confirmar)
    t2 = threading.Thread(target=confirmar)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert erros_inesperados == [], f"vazou exceção não tratada (seria um 500): {erros_inesperados}"
    assert sorted(resultados) == ["falhou_limpo", "sucesso"], resultados

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        quantidade_final = session.execute(
            text("SELECT quantidade_atual FROM estoque WHERE id = :id"), {"id": str(cenario["estoque_id"])}
        ).scalar_one()
        total_movimentacoes = session.execute(
            text("SELECT count(*) FROM movimentacoes_estoque WHERE estoque_id = :id"), {"id": str(cenario["estoque_id"])}
        ).scalar_one()
    assert quantidade_final == 0
    assert total_movimentacoes == 1, "só a venda que sucedeu grava lançamento no ledger"
