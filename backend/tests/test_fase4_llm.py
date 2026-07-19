"""FASE 4 (confiabilidade do LLM). Mesma infraestrutura das fases anteriores
— testes que precisam de banco usam TEST_DATABASE_URL; os que testam só a
lógica de extração/validação contra o histórico de execução do CrewAI são
puros (sem banco, sem LLM real).
"""

import os
import time
import uuid

import pytest

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


def _crew_output_com_mensagens(mensagens: list[dict], pydantic=None):
    from crewai.crews.crew_output import CrewOutput
    from crewai.tasks.task_output import TaskOutput

    task_output = TaskOutput(description="desc", agent="atendente", messages=mensagens)
    return CrewOutput(raw="x", tasks_output=[task_output], pydantic=pydantic)


# ---------------------------------------------------------------------------
# LLM-01: pagamento determinístico — GATE OBRIGATÓRIO da FASE 4.
# ---------------------------------------------------------------------------


def test_gate_sucesso_alucinado_sem_tool_call_nao_e_aprovado() -> None:
    """LLM devolve sucesso=True + transacao_id inventado, mas
    processar_pagamento_mock nunca foi chamada de verdade (sem mensagem
    role='tool' no histórico) — _extrair_resultado_tool tem que devolver
    None, e o fluxo de service.py trata isso como pagamento NÃO aprovado."""
    from app.agents.schemas import ConfirmacaoCompraOutput
    from app.agents.service import _extrair_resultado_tool

    saida_alucinada = ConfirmacaoCompraOutput(
        sucesso=True, resposta_texto="Compra confirmada!", transacao_id="mock_inventado_pelo_llm", nfe_chave="mock_nfe_inventada"
    )
    resultado = _crew_output_com_mensagens(
        mensagens=[
            {"role": "assistant", "content": "Processei o pagamento com sucesso!"},
        ],
        pydantic=saida_alucinada,
    )

    resultado_tool = _extrair_resultado_tool(resultado, "processar_pagamento_mock")
    assert resultado_tool is None, "não houve tool call real — extração tem que devolver None, não confiar no texto do LLM"

    # A decisão de negócio replicada aqui é exatamente a de service.py:
    # pagamento_aprovado só é True se a tool respondeu status='aprovado'.
    pagamento_aprovado = bool(resultado_tool) and resultado_tool.get("status") == "aprovado"
    assert pagamento_aprovado is False


def test_gate_tool_chamada_de_verdade_com_status_aprovado_e_reconhecida() -> None:
    from app.agents.service import _extrair_resultado_tool

    resultado = _crew_output_com_mensagens(
        mensagens=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"function": {"name": "processar_pagamento_mock"}}],
            },
            {
                "role": "tool",
                "name": "processar_pagamento_mock",
                "content": '{"status": "aprovado", "transacao_id": "mock_abc123", "valor_total": 19.8, "forma_pagamento": "cartao"}',
            },
        ]
    )

    resultado_tool = _extrair_resultado_tool(resultado, "processar_pagamento_mock")
    assert resultado_tool == {"status": "aprovado", "transacao_id": "mock_abc123", "valor_total": 19.8, "forma_pagamento": "cartao"}


def test_gate_tool_chamada_com_status_diferente_de_aprovado_nao_e_aprovado() -> None:
    from app.agents.service import _extrair_resultado_tool

    resultado = _crew_output_com_mensagens(
        mensagens=[{"role": "tool", "name": "processar_pagamento_mock", "content": '{"status": "recusado"}'}]
    )
    resultado_tool = _extrair_resultado_tool(resultado, "processar_pagamento_mock")
    pagamento_aprovado = bool(resultado_tool) and resultado_tool.get("status") == "aprovado"
    assert pagamento_aprovado is False


def test_extrair_resultado_tool_json_invalido_devolve_none() -> None:
    from app.agents.service import _extrair_resultado_tool

    resultado = _crew_output_com_mensagens(
        mensagens=[{"role": "tool", "name": "processar_pagamento_mock", "content": "isto não é json"}]
    )
    assert _extrair_resultado_tool(resultado, "processar_pagamento_mock") is None


@requires_db
def test_gate_venda_nao_confirmada_sem_pagamento_real_via_marcar_falha() -> None:
    """Fecha o ciclo: quando o pagamento não é confirmado por tool call real,
    _marcar_venda_falha é chamado e a venda fica com status_aprovacao='falha'
    no banco — nunca 'confirmada'."""
    from sqlalchemy import text

    from app.agents.config import AgentRole
    from app.agents.db_sync import agent_session
    from app.agents.registry import agente_id_for
    from app.agents.service import _marcar_venda_falha
    from app.integrations.sync import _backend_session
    from app.models.enums import CanalVendaEnum, StatusConfirmacaoVendaEnum
    from app.models.venda import Venda

    session = _backend_session()
    try:
        filial_id = session.execute(text("INSERT INTO filiais (nome) VALUES (:n) RETURNING id"), {"n": f"Filial LLM {uuid.uuid4().hex[:8]}"}).scalar_one()
        session.commit()
    finally:
        session.close()

    with agent_session(AgentRole.ATENDENTE) as session:
        venda = Venda(
            filial_id=filial_id,
            agente_atendimento_id=agente_id_for(AgentRole.ATENDENTE),
            canal=CanalVendaEnum.avatar_ia,
            valor_total="10.00",
            status_confirmacao=StatusConfirmacaoVendaEnum.pendente,
            idempotency_key=f"teste-llm01-{uuid.uuid4().hex}",
        )
        session.add(venda)
        session.flush()
        venda_id = venda.id

    _marcar_venda_falha(venda_id, motivo="Teste: pagamento não confirmado por tool call real")

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        status_final = session.execute(text("SELECT status_confirmacao FROM vendas WHERE id = :id"), {"id": str(venda_id)}).scalar_one()
    assert status_final == "falha"


# ---------------------------------------------------------------------------
# LLM-02 / LLM-03: produto_id sempre revalidado; preço/disponibilidade
# sempre do banco, nunca do campo que o LLM devolveu.
# ---------------------------------------------------------------------------


def _criar_produto_manual_llm(*, tarja: str = "isento", preco_tabela: str = "10.00") -> uuid.UUID:
    from sqlalchemy import text as sqltext

    from app.integrations.sync import _backend_session

    session = _backend_session()
    try:
        fabricante_id = session.execute(
            sqltext("INSERT INTO fabricantes (nome) VALUES (:n) RETURNING id"), {"n": f"Fabricante LLM {uuid.uuid4().hex[:8]}"}
        ).scalar_one()
        produto_id = session.execute(
            sqltext(
                """
                INSERT INTO produtos (fabricante_id, nome_comercial, forma_farmaceutica, via_administracao,
                    concentracao_valor, concentracao_unidade, quantidade_embalagem, tarja, preco_tabela)
                VALUES (:f, :n, 'pomada', 'topica', 10, 'mg', 1, :tarja, :preco) RETURNING id
                """
            ),
            {"f": str(fabricante_id), "n": f"Produto LLM {uuid.uuid4().hex[:8]}", "tarja": tarja, "preco": preco_tabela},
        ).scalar_one()
        session.commit()
    finally:
        session.close()
    return produto_id


@requires_db
def test_produto_id_inexistente_e_descartado() -> None:
    from app.agents.service import _validar_produto_sugerido

    validado, motivo = _validar_produto_sugerido(str(uuid.uuid4()), uuid.uuid4(), "sugestão do LLM")
    assert validado is None
    assert motivo is not None and "não encontrado" in motivo


@requires_db
def test_produto_id_nao_e_uuid_valido_e_descartado() -> None:
    from app.agents.service import _validar_produto_sugerido

    validado, motivo = _validar_produto_sugerido("isto-nao-e-um-uuid", uuid.uuid4(), "sugestão do LLM")
    assert validado is None
    assert motivo is not None and "não é um UUID válido" in motivo


@requires_db
def test_produto_controlado_e_invisivel_ao_atendente_e_descartado() -> None:
    """RLS (0012::sel_atendente_mip) já bloqueia — a validação determinística
    só confirma que isso vira descarte limpo, não um crash."""
    from app.agents.service import _validar_produto_sugerido

    produto_id = _criar_produto_manual_llm(tarja="preta")
    validado, motivo = _validar_produto_sugerido(str(produto_id), uuid.uuid4(), "sugestão do LLM (alucinada)")
    assert validado is None
    assert motivo is not None and "não encontrado" in motivo


@requires_db
def test_preco_exibido_vem_do_banco_nao_do_llm() -> None:
    from app.agents.service import _validar_produto_sugerido

    produto_id = _criar_produto_manual_llm(preco_tabela="42.50")
    validado, motivo = _validar_produto_sugerido(str(produto_id), uuid.uuid4(), "sugestão do LLM")

    assert motivo is None
    assert validado is not None
    # Sem lote em estoque -> indisponível, mas o preço ainda vem do banco
    # (preco_tabela como referência), nunca de um campo que o LLM inventou.
    assert validado.disponivel is False
    assert validado.preco == 42.50


@requires_db
def test_preco_exibido_reflete_desconto_aprovado_do_lote() -> None:
    """Fecha LLM-03: o preço mostrado ao cliente na pesquisa é a MESMA
    consulta (preco_efetivo) que decide o preço cobrado na confirmação —
    não dá pra divergir por construção."""
    from datetime import date, timedelta

    from sqlalchemy import text as sqltext

    from app.agents.service import _validar_produto_sugerido
    from app.integrations.sync import _backend_session

    produto_id = _criar_produto_manual_llm(preco_tabela="20.00")

    session = _backend_session()
    try:
        lote_id = session.execute(
            sqltext(
                """
                INSERT INTO lotes (produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
                VALUES (:p, :n, :fab, :val, 10, 8.00, 'disponivel') RETURNING id
                """
            ),
            {"p": str(produto_id), "n": f"L{uuid.uuid4().hex[:8]}", "fab": date.today() - timedelta(days=100), "val": date.today() + timedelta(days=300)},
        ).scalar_one()
        filial_id = session.execute(sqltext("INSERT INTO filiais (nome) VALUES (:n) RETURNING id"), {"n": f"Filial LLM {uuid.uuid4().hex[:8]}"}).scalar_one()
        session.execute(
            sqltext("INSERT INTO estoque (filial_id, lote_id, quantidade_atual, quantidade_reservada) VALUES (:f, :l, 10, 0)"),
            {"f": str(filial_id), "l": str(lote_id)},
        )
        session.commit()
    finally:
        session.close()

    from tests.test_fase3_negocio import _propor_e_aprovar_desconto

    _propor_e_aprovar_desconto(produto_id, lote_id, preco_novo="15.00")

    validado, _ = _validar_produto_sugerido(str(produto_id), filial_id, "sugestão do LLM")
    assert validado is not None
    assert validado.disponivel is True
    assert validado.preco == 15.00, "preço exibido tem que refletir o desconto aprovado, não a tabela original"


# ---------------------------------------------------------------------------
# LLM-04: retry (1 tentativa extra) quando resultado.pydantic vem None;
# fallback seguro se ainda assim vier None. Testado direto em executar_crew,
# com um Crew falso — não depende de banco nem de chamada real ao LLM.
# ---------------------------------------------------------------------------


def test_executar_crew_tenta_de_novo_ate_pydantic_valido() -> None:
    from pydantic import BaseModel

    from app.agents.execucao import executar_crew

    class _SaidaFake(BaseModel):
        ok: bool = True

    chamadas = {"n": 0}

    class FakeCrew:
        def kickoff(self):
            chamadas["n"] += 1
            pydantic_val = None if chamadas["n"] == 1 else _SaidaFake()
            return _crew_output_com_mensagens(mensagens=[], pydantic=pydantic_val)

    execucao = executar_crew(lambda: FakeCrew(), modelo_llm="modelo-teste")

    assert chamadas["n"] == 2, "primeira tentativa veio None — tem que ter tentado de novo"
    assert execucao.tentativas == 2
    assert execucao.resultado is not None
    assert execucao.resultado.pydantic == _SaidaFake()
    assert execucao.timeout is False
    assert execucao.modelo_llm == "modelo-teste"


def test_executar_crew_esgota_tentativas_e_devolve_none() -> None:
    """resultado.pydantic vem None em TODAS as tentativas -> fallback seguro
    (resultado=None), nunca um pydantic inválido silenciosamente aceito."""
    from app.agents.execucao import executar_crew

    class FakeCrewSempreNone:
        def kickoff(self):
            return _crew_output_com_mensagens(mensagens=[], pydantic=None)

    execucao = executar_crew(lambda: FakeCrewSempreNone(), modelo_llm="modelo-teste", tentativas_max=2)

    assert execucao.resultado is None
    assert execucao.tentativas == 2
    assert execucao.timeout is False


# ---------------------------------------------------------------------------
# LLM-05: timeout duro em crew.kickoff(). O ponto crítico aqui não é só "o
# timeout dispara", é "a função devolve controle rápido" — um bug real foi
# encontrado e corrigido nesta mesma fase: `with ThreadPoolExecutor(...)`
# bloqueia no __exit__ até a thread terminar (shutdown(wait=True) é o
# default), o que anulava o timeout inteiro. Por isso o teste mede tempo
# decorrido, não só o resultado.
# ---------------------------------------------------------------------------


def test_executar_crew_timeout_devolve_controle_rapido_e_marca_timeout(monkeypatch) -> None:
    from app.agents import execucao as execucao_module
    from app.agents.config import AgentSettings

    fake_settings = AgentSettings(
        database_url_agente_atendente="postgresql+psycopg2://x/x",
        database_url_agente_estoque="postgresql+psycopg2://x/x",
        database_url_agente_financeiro="postgresql+psycopg2://x/x",
        database_url_agente_orquestrador="postgresql+psycopg2://x/x",
        database_url_agente_tributario="postgresql+psycopg2://x/x",
        crew_timeout_seconds=0.1,
    )
    monkeypatch.setattr(execucao_module, "get_agent_settings", lambda: fake_settings)

    class FakeCrewLenta:
        def kickoff(self):
            time.sleep(1.5)  # bem maior que o timeout de 0.1s configurado acima
            return _crew_output_com_mensagens(mensagens=[], pydantic="nunca deveria ser usado")

    inicio = time.monotonic()
    execucao = execucao_module.executar_crew(lambda: FakeCrewLenta(), modelo_llm="modelo-teste", tentativas_max=1)
    decorrido = time.monotonic() - inicio

    assert decorrido < 1.0, f"executar_crew deveria devolver controle perto de 0.1s, levou {decorrido:.2f}s"
    assert execucao.resultado is None
    assert execucao.timeout is True


# ---------------------------------------------------------------------------
# LLM-07: atendente (fluxo de pesquisa) usa temperatura baixa (0.1), não mais
# 0.3 — texto de sugestão clínica não é lugar pra "criatividade" do modelo.
# ---------------------------------------------------------------------------


def test_atendente_pesquisa_usa_temperatura_baixa() -> None:
    import inspect

    from app.agents import service

    source = inspect.getsource(service._run_atendimento_pesquisa)
    assert "temperature=0.1" in source
    assert "temperature=0.3" not in source


# ---------------------------------------------------------------------------
# LLM-08 + LLM-10 + QA-03: modelo_llm/tokens_totais/latencia_ms persistidos
# em logs_auditoria; atendente resolve pro modelo Flash, os demais pro Pro.
# ---------------------------------------------------------------------------


@requires_db
def test_registrar_auditoria_persiste_modelo_tokens_e_latencia() -> None:
    from sqlalchemy import text

    from app.agents.audit import registrar_auditoria
    from app.agents.config import AgentRole
    from app.agents.db_sync import agent_session
    from app.models.enums import TipoDecisaoEnum

    log_id = registrar_auditoria(
        role=AgentRole.ATENDENTE,
        tipo_decisao=TipoDecisaoEnum.alerta_estoque,
        entidade_afetada="produtos",
        decisao_tomada="teste LLM-08/QA-03",
        dados_base={},
        modelo_llm="gemini/gemini-2.5-flash",
        tokens_totais=1234,
        latencia_ms=567,
    )

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        row = session.execute(
            text("SELECT modelo_llm, tokens_totais, latencia_ms FROM logs_auditoria WHERE id = :id"),
            {"id": str(log_id)},
        ).first()

    assert row.modelo_llm == "gemini/gemini-2.5-flash"
    assert row.tokens_totais == 1234
    assert row.latencia_ms == 567


def test_llm_model_id_atendente_resolve_flash_outras_roles_resolvem_pro() -> None:
    from app.agents.config import AgentRole, AgentSettings

    settings = AgentSettings(
        database_url_agente_atendente="postgresql+psycopg2://x/x",
        database_url_agente_estoque="postgresql+psycopg2://x/x",
        database_url_agente_financeiro="postgresql+psycopg2://x/x",
        database_url_agente_orquestrador="postgresql+psycopg2://x/x",
        database_url_agente_tributario="postgresql+psycopg2://x/x",
        gemini_api_key="fake-key-de-teste",
    )

    assert settings.llm_model_id(AgentRole.ATENDENTE) == "gemini/gemini-flash-latest"
    assert settings.llm_model_id(AgentRole.GERENTE_ESTOQUE) == "gemini/gemini-pro-latest"
    assert settings.llm_model_id(AgentRole.FINANCEIRO) == "gemini/gemini-pro-latest"
    assert settings.llm_model_id(AgentRole.ORQUESTRADOR) == "gemini/gemini-pro-latest"


def test_build_llm_aplica_o_modelo_resolvido_por_role(monkeypatch) -> None:
    from app.agents import llm as llm_module
    from app.agents.config import AgentRole, AgentSettings

    fake_settings = AgentSettings(
        database_url_agente_atendente="postgresql+psycopg2://x/x",
        database_url_agente_estoque="postgresql+psycopg2://x/x",
        database_url_agente_financeiro="postgresql+psycopg2://x/x",
        database_url_agente_orquestrador="postgresql+psycopg2://x/x",
        database_url_agente_tributario="postgresql+psycopg2://x/x",
        gemini_api_key="fake-key-de-teste",
    )
    monkeypatch.setattr(llm_module, "get_agent_settings", lambda: fake_settings)

    llm_atendente = llm_module.build_llm(temperature=0.1, role=AgentRole.ATENDENTE)
    llm_financeiro = llm_module.build_llm(temperature=0.1, role=AgentRole.FINANCEIRO)

    assert "flash" in llm_atendente.model
    assert "pro" in llm_financeiro.model


# ---------------------------------------------------------------------------
# LLM-09: agente_id_for usa TTLCache (5 min), não lru_cache sem expiração —
# um id antigo não pode ficar em memória pra sempre.
# ---------------------------------------------------------------------------


@requires_db
def test_agente_id_for_usa_cache_com_ttl_de_5_minutos() -> None:
    from app.agents import registry
    from app.agents.config import AgentRole

    assert registry._agente_id_cache.ttl == 300, "TTL tem que ser 5 minutos (300s), não cache eterno"

    registry._agente_id_cache.clear()
    assert registry._agente_id_cache.currsize == 0
    id1 = registry.agente_id_for(AgentRole.ATENDENTE)
    assert registry._agente_id_cache.currsize == 1, "a chamada tem que ter preenchido o cache"

    id2 = registry.agente_id_for(AgentRole.ATENDENTE)
    assert id1 == id2, "segunda chamada dentro do TTL tem que devolver o mesmo id cacheado"
    assert registry._agente_id_cache.currsize == 1, "cache hit não deveria criar uma segunda entrada"

    # Simula a expiração (sem esperar 5 min de verdade): limpar o cache é
    # equivalente, do ponto de vista do comportamento observável, a ele ter
    # expirado — a próxima chamada tem que voltar a consultar o banco.
    registry._agente_id_cache.clear()
    assert registry._agente_id_cache.currsize == 0
    id3 = registry.agente_id_for(AgentRole.ATENDENTE)
    assert id3 == id1


# ---------------------------------------------------------------------------
# LLM-06: histórico de conversa persistido por sessao_id, últimas N (10)
# recuperadas em ordem cronológica.
# ---------------------------------------------------------------------------


@requires_db
def test_historico_sessao_persiste_e_recupera_em_ordem_cronologica() -> None:
    from app.agents.service import _buscar_historico_sessao, _formatar_historico_chat, _registrar_mensagem_sessao

    sessao_id = uuid.uuid4()
    _registrar_mensagem_sessao(sessao_id, "cliente", "Primeira mensagem")
    _registrar_mensagem_sessao(sessao_id, "avatar", "Primeira resposta")
    _registrar_mensagem_sessao(sessao_id, "cliente", "Segunda mensagem")

    historico = _buscar_historico_sessao(sessao_id)
    assert [h["mensagem"] for h in historico] == ["Primeira mensagem", "Primeira resposta", "Segunda mensagem"]

    texto = _formatar_historico_chat(sessao_id)
    assert texto.startswith("<historico_conversa>")
    assert texto.endswith("</historico_conversa>")
    assert "Primeira mensagem" in texto
    assert "Segunda mensagem" in texto


@requires_db
def test_historico_sessao_respeita_limite_e_mantem_ordem() -> None:
    from app.agents.service import _buscar_historico_sessao, _registrar_mensagem_sessao

    sessao_id = uuid.uuid4()
    for i in range(15):
        _registrar_mensagem_sessao(sessao_id, "cliente", f"mensagem {i}")

    historico = _buscar_historico_sessao(sessao_id, limite=10)
    assert len(historico) == 10
    # As 10 mais recentes (5..14), em ordem cronológica (mais antiga primeiro).
    assert [h["mensagem"] for h in historico] == [f"mensagem {i}" for i in range(5, 15)]


@requires_db
def test_historico_sessao_vazio_devolve_texto_padrao() -> None:
    from app.agents.service import _formatar_historico_chat

    texto = _formatar_historico_chat(uuid.uuid4())
    assert "Nenhum histórico anterior" in texto
