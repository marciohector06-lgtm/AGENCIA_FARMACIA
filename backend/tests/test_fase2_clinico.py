"""FASE 2 (clínico). Mesma infraestrutura das fases anteriores — precisa de
TEST_DATABASE_URL + migrations 0001-0022 aplicadas e credenciais de agente.
"""

import os
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.integrations.sync import _backend_session

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


# ---------------------------------------------------------------------------
# CLIN-04: formatação do perfil clínico (puro, sem banco)
# ---------------------------------------------------------------------------


def _request_base(**overrides):
    from app.schemas.chat import ChatAtendimentoRequest

    payload = {"filial_id": uuid.uuid4(), "mensagem": "dor de cabeça", **overrides}
    return ChatAtendimentoRequest(**payload)


def test_perfil_clinico_vazio_quando_nada_informado() -> None:
    from app.agents.service import _formatar_perfil_clinico

    assert _formatar_perfil_clinico(_request_base()) == "Nenhum perfil clínico informado pelo cliente."


def test_perfil_clinico_inclui_medicamentos_delimitados() -> None:
    from app.agents.service import _formatar_perfil_clinico

    request = _request_base(medicamentos_em_uso=["varfarina", "losartana"], gestante=True, idade=45)
    resultado = _formatar_perfil_clinico(request)
    assert "<cliente_input>varfarina; losartana</cliente_input>" in resultado
    assert "Gestante: sim" in resultado
    assert "Idade: 45" in resultado


# ---------------------------------------------------------------------------
# CLIN-05: guardrail determinístico (puro, sem banco, sem LLM) — constrói um
# CrewOutput/TaskOutput reais com o formato de mensagens que o CrewAI produz
# de verdade (role='tool', name=<nome da tool>), para provar que o guardrail
# olha o histórico de execução, não o que o LLM diz que fez.
# ---------------------------------------------------------------------------


def _crew_output_com_mensagens(mensagens: list[dict]):
    from crewai.crews.crew_output import CrewOutput
    from crewai.tasks.task_output import TaskOutput

    task_output = TaskOutput(description="desc", agent="atendente", messages=mensagens)
    return CrewOutput(raw="x", tasks_output=[task_output])


def test_tool_foi_chamada_confirma_por_mensagem_role_tool() -> None:
    from app.agents.service import _tool_foi_chamada

    resultado = _crew_output_com_mensagens(
        [
            {"role": "assistant", "content": None, "tool_calls": [{"function": {"name": "consultar_interacoes"}}]},
            {"role": "tool", "name": "consultar_interacoes", "content": "{}"},
        ]
    )
    assert _tool_foi_chamada(resultado, "consultar_interacoes") is True


def test_tool_foi_chamada_falso_se_llm_so_disse_que_chamou_mas_nao_ha_mensagem_tool() -> None:
    """O ponto central do CLIN-05: o LLM pode "alucinar" que chamou (ex.: só
    o tool_calls do assistant, sem a mensagem role='tool' correspondente
    confirmando execução) — o guardrail não pode se enganar com isso."""
    from app.agents.service import _tool_foi_chamada

    resultado = _crew_output_com_mensagens(
        [
            {"role": "assistant", "content": "Chamei consultar_interacoes e está tudo certo!"},
        ]
    )
    assert _tool_foi_chamada(resultado, "consultar_interacoes") is False


def test_tool_foi_chamada_falso_quando_outra_tool_foi_chamada() -> None:
    from app.agents.service import _tool_foi_chamada

    resultado = _crew_output_com_mensagens(
        [{"role": "tool", "name": "consultar_restricoes_uso", "content": "{}"}]
    )
    assert _tool_foi_chamada(resultado, "consultar_interacoes") is False


def test_tool_foi_chamada_falso_quando_nao_ha_mensagens() -> None:
    from app.agents.service import _tool_foi_chamada

    assert _tool_foi_chamada(_crew_output_com_mensagens([]), "consultar_interacoes") is False


def _criar_produto_lote_estoque_manual(
    *, quantidade: int, data_validade: date, status: str = "disponivel"
) -> dict:
    """Monta produto/lote/estoque direto via SQL (app_backend), sem passar
    pela API — mais rápido e preciso pra montar os cenários de borda do FEFO
    (lote vencido, bloqueado, etc.) que a API não deixaria criar diretamente
    de qualquer forma (LoteCreate não aceita status na criação)."""
    session = _backend_session()
    try:
        fabricante_id = session.execute(
            text("INSERT INTO fabricantes (nome) VALUES (:n) RETURNING id"),
            {"n": f"Fabricante FEFO {uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        produto_id = session.execute(
            text(
                """
                INSERT INTO produtos (fabricante_id, nome_comercial, forma_farmaceutica, via_administracao,
                    concentracao_valor, concentracao_unidade, quantidade_embalagem, tarja, preco_tabela)
                VALUES (:fabricante_id, :nome, 'pomada', 'topica', 10, 'mg', 1, 'isento', 9.90)
                RETURNING id
                """
            ),
            {"fabricante_id": str(fabricante_id), "nome": f"Produto FEFO {uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        lote_id = session.execute(
            text(
                """
                INSERT INTO lotes (produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
                VALUES (:produto_id, :numero, :data_fabricacao, :data_validade, :qtd, 1.00, :status)
                RETURNING id
                """
            ),
            {
                "produto_id": str(produto_id),
                "numero": f"L{uuid.uuid4().hex[:8]}",
                "data_fabricacao": data_validade - timedelta(days=365),
                "data_validade": data_validade,
                "qtd": quantidade,
                "status": status,
            },
        ).scalar_one()
        filial_id = session.execute(
            text("INSERT INTO filiais (nome) VALUES (:n) RETURNING id"),
            {"n": f"Filial FEFO {uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        estoque_id = session.execute(
            text(
                "INSERT INTO estoque (filial_id, lote_id, quantidade_atual, quantidade_reservada) "
                "VALUES (:filial_id, :lote_id, :qtd, 0) RETURNING id"
            ),
            {"filial_id": str(filial_id), "lote_id": str(lote_id), "qtd": quantidade},
        ).scalar_one()
        session.commit()
    finally:
        session.close()
    return {"produto_id": produto_id, "lote_id": lote_id, "filial_id": filial_id, "estoque_id": estoque_id}


@requires_db
def test_lote_vencido_nao_aparece_na_view_nem_e_selecionado_pelo_fefo() -> None:
    """Teste obrigatório (CLIN-01/CLIN-02): lote com data_validade = ontem,
    quantidade > 0 e status='disponivel' não pode aparecer em vw_estoque_atual
    nem ser escolhido por _buscar_lote_disponivel."""
    from app.agents.service import _buscar_lote_disponivel

    cenario = _criar_produto_lote_estoque_manual(quantidade=50, data_validade=date.today() - timedelta(days=1))

    with agent_session(AgentRole.ATENDENTE) as session:
        na_view = session.execute(
            text("SELECT 1 FROM vw_estoque_atual WHERE lote_id = :id"), {"id": str(cenario["lote_id"])}
        ).first()
    assert na_view is None, "lote vencido não pode aparecer em vw_estoque_atual"

    lote_selecionado = _buscar_lote_disponivel(cenario["produto_id"], cenario["filial_id"], 1)
    assert lote_selecionado is None, "_buscar_lote_disponivel não pode selecionar lote vencido"


@requires_db
def test_lote_bloqueado_nao_aparece_mesmo_com_validade_ok() -> None:
    from app.agents.service import _buscar_lote_disponivel

    cenario = _criar_produto_lote_estoque_manual(
        quantidade=50, data_validade=date.today() + timedelta(days=365), status="bloqueado"
    )
    lote_selecionado = _buscar_lote_disponivel(cenario["produto_id"], cenario["filial_id"], 1)
    assert lote_selecionado is None


@requires_db
def test_fefo_escolhe_o_lote_valido_que_vence_primeiro() -> None:
    from app.agents.service import _buscar_lote_disponivel

    session = _backend_session()
    try:
        fabricante_id = session.execute(
            text("INSERT INTO fabricantes (nome) VALUES (:n) RETURNING id"), {"n": f"Fab {uuid.uuid4().hex[:8]}"}
        ).scalar_one()
        produto_id = session.execute(
            text(
                """
                INSERT INTO produtos (fabricante_id, nome_comercial, forma_farmaceutica, via_administracao,
                    concentracao_valor, concentracao_unidade, quantidade_embalagem, tarja, preco_tabela)
                VALUES (:f, :n, 'pomada', 'topica', 10, 'mg', 1, 'isento', 9.90) RETURNING id
                """
            ),
            {"f": str(fabricante_id), "n": f"Produto FEFO Multi {uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        filial_id = session.execute(
            text("INSERT INTO filiais (nome) VALUES (:n) RETURNING id"), {"n": f"Filial {uuid.uuid4().hex[:8]}"}
        ).scalar_one()

        lotes = {}
        for rotulo, dias in [("vencido", -1), ("vence_em_10", 10), ("vence_em_100", 100)]:
            lote_id = session.execute(
                text(
                    """
                    INSERT INTO lotes (produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
                    VALUES (:p, :n, :fab, :val, 20, 1.00, 'disponivel') RETURNING id
                    """
                ),
                {
                    "p": str(produto_id),
                    "n": f"L-{rotulo}-{uuid.uuid4().hex[:6]}",
                    "fab": date.today() - timedelta(days=400),
                    "val": date.today() + timedelta(days=dias),
                },
            ).scalar_one()
            session.execute(
                text("INSERT INTO estoque (filial_id, lote_id, quantidade_atual, quantidade_reservada) VALUES (:f, :l, 20, 0)"),
                {"f": str(filial_id), "l": str(lote_id)},
            )
            lotes[rotulo] = lote_id
        session.commit()
    finally:
        session.close()

    escolhido = _buscar_lote_disponivel(produto_id, filial_id, 5)
    assert escolhido == lotes["vence_em_10"], "FEFO deve escolher o lote válido que vence primeiro, ignorando o vencido"


@requires_db
def test_fefo_recusa_lote_com_quantidade_insuficiente() -> None:
    from app.agents.service import _buscar_lote_disponivel

    cenario = _criar_produto_lote_estoque_manual(quantidade=3, data_validade=date.today() + timedelta(days=100))
    assert _buscar_lote_disponivel(cenario["produto_id"], cenario["filial_id"], 3) == cenario["lote_id"]
    assert _buscar_lote_disponivel(cenario["produto_id"], cenario["filial_id"], 4) is None
