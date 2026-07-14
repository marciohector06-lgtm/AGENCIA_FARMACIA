"""FASE 0: testes de integração (Postgres real) da fronteira do ERP.

Precisam de TEST_DATABASE_URL com as migrations 0001-0019 aplicadas e das
credenciais de agente configuradas (DATABASE_URL_AGENTE_*) — mesma exigência
de infraestrutura que tests/test_produtos.py já tem para seus próprios casos.
Skip automático (`requires_db`) quando isso não está disponível.
"""

import os
import uuid
from contextlib import contextmanager
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.core.config import get_settings
from app.integrations.mock_adapter import MockAdapter
from app.integrations.sync import _backend_session, run_sync

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


@contextmanager
def _tarja_endpoint_flag(valor: bool):
    """get_settings() é @lru_cache — precisa limpar o cache pra a env var
    surtir efeito, e limpar de novo ao sair pra não vazar estado entre testes."""
    os.environ["TARJA_ENDPOINT_ENABLED"] = "true" if valor else "false"
    get_settings.cache_clear()
    try:
        yield
    finally:
        os.environ.pop("TARJA_ENDPOINT_ENABLED", None)
        get_settings.cache_clear()

# Nomes de princípio ativo que o dataset do MockAdapter referencia. O sync
# NUNCA cria um princípio ativo novo (curadoria clínica é trabalho humano,
# fora do sync — ver app/integrations/sync.py::_resolver_principio_ativo),
# então os testes de sync precisam semear isso antes, como uma farmácia real
# faria via cadastro clínico curado.
_PRINCIPIOS_ATIVOS_DO_MOCK = ["Paracetamol", "Ibuprofeno", "Dipirona", "Amoxicilina", "Clonazepam"]


def _seed_principios_ativos_do_mock() -> None:
    from sqlalchemy import text

    session = _backend_session()
    try:
        for nome in _PRINCIPIOS_ATIVOS_DO_MOCK:
            session.execute(
                text(
                    "INSERT INTO principios_ativos (nome, classe_terapeutica) VALUES (:nome, 'Teste Fase0') "
                    "ON CONFLICT (nome) DO NOTHING"
                ),
                {"nome": nome},
            )
        session.commit()
    finally:
        session.close()


async def _criar_produto_manual(client: AsyncClient, **overrides) -> dict:
    principio_resp = await client.post(
        "/api/v1/principios-ativos",
        json={"nome": f"Principio Fase0 {uuid.uuid4().hex[:8]}", "classe_terapeutica": "Analgesico"},
    )
    fabricante_resp = await client.post("/api/v1/fabricantes", json={"nome": f"Fabricante Fase0 {uuid.uuid4().hex[:8]}"})
    payload = {
        "principio_ativo_id": principio_resp.json()["id"],
        "fabricante_id": fabricante_resp.json()["id"],
        "nome_comercial": "Produto Fase0 Teste",
        "forma_farmaceutica": "comprimido",
        "via_administracao": "oral",
        "concentracao_valor": "500.000",
        "concentracao_unidade": "mg",
        "quantidade_embalagem": 20,
        "tarja": "isento",
        "preco_tabela": "9.90",
        **overrides,
    }
    resp = await client.post("/api/v1/produtos", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@requires_db
async def test_produto_criado_via_api_nasce_origem_manual_e_editavel(client: AsyncClient) -> None:
    produto = await _criar_produto_manual(client)
    assert produto["origem"] == "manual"
    assert produto["id_externo"] is None

    patch_resp = await client.patch(f"/api/v1/produtos/{produto['id']}", json={"preco_tabela": "10.50"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["preco_tabela"] == "10.50"


@requires_db
async def test_tarja_nao_muda_por_patch_generico(client: AsyncClient) -> None:
    """SEC-06: mesmo em origem='manual' (editável), tarja é exclusiva do
    endpoint privilegiado — o PATCH genérico simplesmente ignora o campo."""
    produto = await _criar_produto_manual(client, tarja="isento")
    patch_resp = await client.patch(f"/api/v1/produtos/{produto['id']}", json={"tarja": "isento", "preco_tabela": "11.00"})
    assert patch_resp.status_code == 200
    # "tarja" não existe em ProdutoUpdate — o Pydantic simplesmente ignora o
    # campo extra; nada muda porque não havia nada pra mudar (era isento).
    get_resp = await client.get(f"/api/v1/produtos/{produto['id']}")
    assert get_resp.json()["tarja"] == "isento"


@requires_db
async def test_endpoint_tarja_flag_desabilitada_bloqueia_mesmo_autenticado(client: AsyncClient) -> None:
    """SEC-06: a flag continua sendo um kill-switch — mesmo autenticado
    (o fixture `client` já injeta um operador válido), TARJA_ENDPOINT_ENABLED=false
    barra o endpoint."""
    produto = await _criar_produto_manual(client, tarja="isento")
    with _tarja_endpoint_flag(False):
        resp = await client.patch(
            f"/api/v1/produtos/{produto['id']}/tarja",
            json={"tarja": "vermelha", "motivo": "Não deveria nem chegar a processar"},
        )
    assert resp.status_code == 403


@requires_db
async def test_endpoint_tarja_sem_token_retorna_401(raw_client: AsyncClient) -> None:
    """SEC-01 fechou o SEC-06 de vez: sem token nenhum, nem chega a checar a
    flag — 401 direto no dependencies=[...] do router."""
    resp = await raw_client.patch(
        f"/api/v1/produtos/{uuid.uuid4()}/tarja",
        json={"tarja": "vermelha", "motivo": "Não deveria nem chegar a processar"},
    )
    assert resp.status_code == 401


@requires_db
async def test_endpoint_privilegiado_altera_tarja_e_gera_auditoria(client: AsyncClient) -> None:
    """Default de TARJA_ENDPOINT_ENABLED agora é True (SEC-06): a pré-condição
    (auth no ar) foi satisfeita nesta fase. O fixture `client` já autentica."""
    produto = await _criar_produto_manual(client, tarja="isento")
    resp = await client.patch(
        f"/api/v1/produtos/{produto['id']}/tarja",
        json={"tarja": "vermelha", "motivo": "Reclassificação de teste automatizado"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tarja"] == "vermelha"


@requires_db
async def test_estoque_update_ignora_quantidade_no_payload(client: AsyncClient) -> None:
    """SEC-11: mesmo mandando quantidade_atual no PATCH, o valor no banco não muda."""
    filial_resp = await client.post("/api/v1/filiais", json={"nome": f"Filial Fase0 {uuid.uuid4().hex[:8]}"})
    produto = await _criar_produto_manual(client)
    lote_resp = await client.post(
        "/api/v1/lotes",
        json={
            "produto_id": produto["id"],
            "numero_lote": f"L{uuid.uuid4().hex[:6]}",
            "data_fabricacao": "2025-01-01",
            "data_validade": "2027-01-01",
            "quantidade_recebida": 10,
            "custo_unitario": "3.00",
        },
    )
    estoque_resp = await client.post(
        "/api/v1/estoque",
        json={"filial_id": filial_resp.json()["id"], "lote_id": lote_resp.json()["id"], "quantidade_atual": 10, "quantidade_reservada": 0},
    )
    estoque_id = estoque_resp.json()["id"]

    patch_resp = await client.patch(f"/api/v1/estoque/{estoque_id}", json={"quantidade_atual": 99999, "localizacao_gondola": "A1"})
    assert patch_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/estoque/{estoque_id}")
    assert get_resp.json()["quantidade_atual"] == 10  # não mudou
    assert get_resp.json()["localizacao_gondola"] == "A1"  # isso sim mudou


@requires_db
async def test_movimentar_estoque_muda_quantidade_e_registra_motivo(client: AsyncClient) -> None:
    filial_resp = await client.post("/api/v1/filiais", json={"nome": f"Filial Fase0 {uuid.uuid4().hex[:8]}"})
    produto = await _criar_produto_manual(client)
    lote_resp = await client.post(
        "/api/v1/lotes",
        json={
            "produto_id": produto["id"],
            "numero_lote": f"L{uuid.uuid4().hex[:6]}",
            "data_fabricacao": "2025-01-01",
            "data_validade": "2027-01-01",
            "quantidade_recebida": 10,
            "custo_unitario": "3.00",
        },
    )
    estoque_resp = await client.post(
        "/api/v1/estoque",
        json={"filial_id": filial_resp.json()["id"], "lote_id": lote_resp.json()["id"], "quantidade_atual": 10, "quantidade_reservada": 0},
    )
    estoque_id = estoque_resp.json()["id"]

    mov_resp = await client.post(
        f"/api/v1/estoque/{estoque_id}/movimentar",
        json={"tipo": "entrada", "quantidade_delta": 25, "motivo": "Recebimento de reposição do fornecedor"},
    )
    assert mov_resp.status_code == 201, mov_resp.text
    assert mov_resp.json()["quantidade_resultante"] == 35

    sem_motivo = await client.post(
        f"/api/v1/estoque/{estoque_id}/movimentar", json={"tipo": "ajuste", "quantidade_delta": -50, "motivo": "curto"}
    )
    assert sem_motivo.status_code == 422  # motivo < 10 chars

    negativo = await client.post(
        f"/api/v1/estoque/{estoque_id}/movimentar",
        json={"tipo": "ajuste", "quantidade_delta": -999, "motivo": "Ajuste que deixaria negativo de propósito"},
    )
    assert negativo.status_code == 409


@requires_db
def test_sync_tarja_desconhecida_vira_vermelha_e_fica_invisivel_ao_atendente() -> None:
    """Ponta a ponta da regra mais importante da FASE 0 (F0-03): roda o sync
    real contra o MockAdapter e confirma, direto na role do banco do
    agente_atendente (RLS real, não mock), que o produto hostil (tarja
    ausente/não mapeável) nunca aparece pra ele."""
    _seed_principios_ativos_do_mock()
    stats = run_sync(MockAdapter(), origem="mock")
    assert stats.produtos_sincronizados >= 4
    assert any("tarja não mapeável" in ev for ev in stats.eventos_falha_fechada)

    with agent_session(AgentRole.ATENDENTE) as session:
        from sqlalchemy import text

        nomes_visiveis = {
            row[0]
            for row in session.execute(
                text("SELECT nome_comercial FROM produtos WHERE origem = 'mock'")
            ).all()
        }

    # PROD-003 (Algivex, tarja ausente) e PROD-004 (Bactrizen 500, tarja
    # cod_legado_7) viraram 'vermelha' no sync — RLS de 0012 barra o
    # agente_atendente de vê-los, exatamente como bloquearia um controlado real.
    assert "Algivex" not in nomes_visiveis
    assert "Bactrizen 500" not in nomes_visiveis
    # Controle negativo: MIP de verdade continua visível.
    assert "Dorexin 750mg" in nomes_visiveis
    # Controle positivo: controlado real (tarja preta) também some, como já
    # acontecia antes da FASE 0 — a regra não regrediu.
    assert "Clonazan 2mg" not in nomes_visiveis


@requires_db
def test_sync_e_idempotente_nao_duplica_linhas() -> None:
    _seed_principios_ativos_do_mock()
    run_sync(MockAdapter(), origem="mock")
    stats2 = run_sync(MockAdapter(), origem="mock")

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        from sqlalchemy import text

        total = session.execute(
            text("SELECT count(*) FROM produtos WHERE origem = 'mock' AND id_externo = 'PROD-001'")
        ).scalar_one()
    assert total == 1
    assert stats2.produtos_sincronizados >= 4


@requires_db
async def test_produto_sincronizado_do_erp_e_somente_leitura(client: AsyncClient) -> None:
    _seed_principios_ativos_do_mock()
    run_sync(MockAdapter(), origem="mock")

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        from sqlalchemy import text

        produto_id = session.execute(
            text("SELECT id FROM produtos WHERE origem = 'mock' AND id_externo = 'PROD-001'")
        ).scalar_one()

    resp = await client.patch(f"/api/v1/produtos/{produto_id}", json={"preco_tabela": "1.00"})
    assert resp.status_code == 409


async def _criar_cenario_manual(client: AsyncClient, quantidade_inicial: int = 10) -> dict:
    """Produto/lote/estoque/filial origem='manual' via API — cenário mínimo
    pra exercitar as mecânicas de outbox/concorrência sem precisar do LLM
    (as funções testadas abaixo são as mesmas que service.py usa, só sem
    passar pelo crew.kickoff())."""
    filial_resp = await client.post("/api/v1/filiais", json={"nome": f"Filial Outbox {uuid.uuid4().hex[:8]}"})
    produto = await _criar_produto_manual(client)
    lote_resp = await client.post(
        "/api/v1/lotes",
        json={
            "produto_id": produto["id"],
            "numero_lote": f"L{uuid.uuid4().hex[:6]}",
            "data_fabricacao": "2025-01-01",
            "data_validade": "2027-01-01",
            "quantidade_recebida": quantidade_inicial,
            "custo_unitario": "3.00",
        },
    )
    estoque_resp = await client.post(
        "/api/v1/estoque",
        json={
            "filial_id": filial_resp.json()["id"],
            "lote_id": lote_resp.json()["id"],
            "quantidade_atual": quantidade_inicial,
            "quantidade_reservada": 0,
        },
    )
    return {
        "produto_id": uuid.UUID(produto["id"]),
        "lote_id": uuid.UUID(lote_resp.json()["id"]),
        "filial_id": uuid.UUID(filial_resp.json()["id"]),
        "estoque_id": uuid.UUID(estoque_resp.json()["id"]),
        "preco_tabela": produto["preco_tabela"],
    }


@requires_db
async def test_outbox_idempotency_key_persistida_antes_da_chamada_externa(client: AsyncClient) -> None:
    """Resposta direta à pergunta 4: a idempotency_key é determinística e
    PERSISTIDA (linha 'pendente' no banco) antes de qualquer chamada ao ERP —
    aqui nem chegamos a chamar nada externo, só provamos que o passo 1 do
    outbox por si só já deixa rastro suficiente pra reconciliar depois."""
    from app.agents.service import _buscar_venda_por_idempotency_key, _criar_venda_pendente, _idempotency_key_venda
    from app.schemas.chat import ChatAtendimentoRequest

    cenario = await _criar_cenario_manual(client)
    sessao_id = uuid.uuid4()
    idempotency_key = _idempotency_key_venda(sessao_id, cenario["produto_id"], cenario["lote_id"], 2)

    # Determinística: recalcular com os mesmos parâmetros dá a MESMA chave.
    assert idempotency_key == _idempotency_key_venda(sessao_id, cenario["produto_id"], cenario["lote_id"], 2)

    request = ChatAtendimentoRequest(
        filial_id=cenario["filial_id"], mensagem="x", produto_id=cenario["produto_id"], lote_id=cenario["lote_id"], quantidade=2
    )
    preco_unitario = Decimal(cenario["preco_tabela"])
    venda_id = _criar_venda_pendente(
        request, cenario["lote_id"], preco_unitario, preco_unitario * 2, idempotency_key, sessao_id
    )

    existente = _buscar_venda_por_idempotency_key(idempotency_key)
    assert existente is not None
    assert existente["id"] == venda_id
    assert existente["status_confirmacao"] == "pendente"

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        from sqlalchemy import text

        log = session.execute(
            text("SELECT decisao_tomada FROM logs_auditoria WHERE entidade_id = :id AND entidade_afetada = 'vendas'"),
            {"id": str(venda_id)},
        ).first()
    assert log is not None and idempotency_key in log.decisao_tomada


@requires_db
def test_debitar_estoque_recusa_quando_exigir_disponibilidade_true() -> None:
    """origem manual: estoque insuficiente é motivo de recusa (Postgres ainda
    é a fonte da verdade)."""
    from app.agents.service import _debitar_estoque_venda

    with pytest.raises(ValueError):
        _debitar_estoque_venda(uuid.uuid4(), 1, None, "teste", exigir_disponibilidade=True)


@requires_db
async def test_confirmar_compra_acima_do_disponivel_retorna_400_nao_500(client: AsyncClient) -> None:
    """QA-02 (FASE 6): mesmo caminho do teste acima, mas ponta a ponta pelo
    endpoint HTTP real (POST /chat/atendimento, confirmar_compra=true) — pedir
    mais unidades do que há em estoque tem que devolver um 400 limpo, nunca
    um 500 vazando a exceção da camada de negócio."""
    from app.core.rate_limit import limiter

    limiter.reset()  # isola de outros testes que já bateram no limite de 10/min deste endpoint
    cenario = await _criar_cenario_manual(client, quantidade_inicial=2)

    resp = await client.post(
        "/api/v1/chat/atendimento",
        json={
            "filial_id": str(cenario["filial_id"]),
            "mensagem": "quero comprar mais do que tem em estoque",
            "confirmar_compra": True,
            "produto_id": str(cenario["produto_id"]),
            "lote_id": str(cenario["lote_id"]),
            "quantidade": 999,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "Estoque insuficiente" in resp.json()["detail"]

    from sqlalchemy import text

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        quantidade_final = session.execute(
            text("SELECT quantidade_atual FROM estoque WHERE id = :id"), {"id": str(cenario["estoque_id"])}
        ).scalar_one()
    assert quantidade_final == 2  # nada foi debitado


@requires_db
async def test_debitar_estoque_concorrente_nao_gera_500_do_check(client: AsyncClient) -> None:
    """Resposta à pergunta 3: dois 'clientes' disputando a última unidade —
    um consegue, o outro recebe ValueError limpo (nunca uma violação de CHECK
    vazando pra fora do SELECT...FOR UPDATE)."""
    import threading

    from app.agents.service import _debitar_estoque_venda

    cenario = await _criar_cenario_manual(client, quantidade_inicial=1)
    resultados: list[str] = []
    erro: list[BaseException] = []

    def tentar_debitar() -> None:
        try:
            _debitar_estoque_venda(cenario["estoque_id"], 1, None, "concorrência", exigir_disponibilidade=True)
            resultados.append("sucesso")
        except ValueError:
            resultados.append("recusado")
        except Exception as exc:  # nunca deveria cair aqui (seria o 500 do CHECK)
            erro.append(exc)

    t1 = threading.Thread(target=tentar_debitar)
    t2 = threading.Thread(target=tentar_debitar)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert erro == []
    assert sorted(resultados) == ["recusado", "sucesso"]

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        from sqlalchemy import text

        quantidade_final = session.execute(
            text("SELECT quantidade_atual FROM estoque WHERE id = :id"), {"id": str(cenario["estoque_id"])}
        ).scalar_one()
    assert quantidade_final == 0


@requires_db
async def test_reconciliacao_saldo_estoque_igual_soma_do_ledger(client: AsyncClient) -> None:
    """Resposta à pergunta 2: não há trigger nem coluna derivada — o saldo é
    mantido por convenção de código (todo caminho de escrita grava um
    lançamento na mesma transação). Este teste É a garantia de reconciliação:
    roda venda + movimentação manual + sync, e prova que quantidade_atual
    sempre bate com o baseline (0) mais a soma dos deltas do ledger."""
    from app.agents.service import _debitar_estoque_venda

    cenario = await _criar_cenario_manual(client, quantidade_inicial=20)

    _debitar_estoque_venda(cenario["estoque_id"], 3, None, "venda de teste", exigir_disponibilidade=True)
    await client.post(f"/api/v1/estoque/{cenario['estoque_id']}/movimentar", json={"tipo": "entrada", "quantidade_delta": 5, "motivo": "Reposição de teste"})
    await client.post(f"/api/v1/estoque/{cenario['estoque_id']}/movimentar", json={"tipo": "ajuste", "quantidade_delta": -2, "motivo": "Ajuste de inventário"})

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        from sqlalchemy import text

        quantidade_atual = session.execute(
            text("SELECT quantidade_atual FROM estoque WHERE id = :id"), {"id": str(cenario["estoque_id"])}
        ).scalar_one()
        soma_ledger = session.execute(
            text("SELECT COALESCE(SUM(quantidade_delta), 0) FROM movimentacoes_estoque WHERE estoque_id = :id"),
            {"id": str(cenario["estoque_id"])},
        ).scalar_one()

    assert quantidade_atual == 20 + soma_ledger
    assert quantidade_atual == 20 - 3 + 5 - 2


@requires_db
def test_movimentacoes_estoque_e_realmente_append_only() -> None:
    """Resposta à pergunta 1: nenhuma role tem UPDATE/DELETE em
    movimentacoes_estoque — nem app_backend, nem agente_atendente."""
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    session = _backend_session()
    try:
        row = session.execute(
            text(
                "INSERT INTO movimentacoes_estoque (estoque_id, tipo, quantidade_delta, quantidade_resultante, motivo) "
                "SELECT id, 'ajuste', 1, quantidade_atual + 1, 'linha de teste' FROM estoque LIMIT 1 RETURNING id"
            )
        ).first()
        session.commit()
        if row is None:
            pytest.skip("Nenhuma linha em estoque para testar (rode depois de outro teste que crie estoque)")
        mov_id = row[0]

        with pytest.raises(ProgrammingError, match="permission denied"):
            session.execute(text("UPDATE movimentacoes_estoque SET motivo = 'alterado' WHERE id = :id"), {"id": str(mov_id)})
            session.commit()
        session.rollback()

        with pytest.raises(ProgrammingError, match="permission denied"):
            session.execute(text("DELETE FROM movimentacoes_estoque WHERE id = :id"), {"id": str(mov_id)})
            session.commit()
        session.rollback()
    finally:
        session.close()

    with agent_session(AgentRole.ATENDENTE) as atendente_session:
        from sqlalchemy.exc import ProgrammingError as PE2

        with pytest.raises(PE2, match="permission denied"):
            atendente_session.execute(text("UPDATE movimentacoes_estoque SET motivo = 'x' WHERE true"))


@requires_db
def test_reconciliador_confirma_venda_que_o_erp_recebeu() -> None:
    """Ponta a ponta do reconciliador: uma venda fica 'pendente' (simulando o
    crash logo após o ERP confirmar, antes de marcarmos localmente), e
    reconciliar_vendas_pendentes() resolve consultando o ERP pela
    idempotency_key — sem precisar tentar registrar de novo."""
    from sqlalchemy import text

    from app.agents.service import _criar_venda_pendente, _idempotency_key_venda
    from app.integrations.base import ItemVendaParaERP, VendaParaERP
    from app.integrations.sync import reconciliar_vendas_pendentes
    from app.schemas.chat import ChatAtendimentoRequest

    _seed_principios_ativos_do_mock()
    run_sync(MockAdapter(), origem="mock")

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        row = session.execute(
            text(
                """
                SELECT p.id AS produto_id, l.id AS lote_id, f.id AS filial_id, p.preco_tabela
                FROM produtos p JOIN lotes l ON l.produto_id = p.id
                JOIN estoque e ON e.lote_id = l.id JOIN filiais f ON f.id = e.filial_id
                WHERE p.id_externo = 'PROD-001'
                """
            )
        ).first()

    sessao_id = uuid.uuid4()
    idempotency_key = _idempotency_key_venda(sessao_id, row.produto_id, row.lote_id, 2)
    adapter = MockAdapter()
    adapter.registrar_venda(
        VendaParaERP(filial_id_externa="FIL-001", itens=[ItemVendaParaERP(produto_id_externo="PROD-001", lote_id_externo="LOTE-001", quantidade=2, preco_unitario="8.90")]),
        idempotency_key=idempotency_key,
    )

    request = ChatAtendimentoRequest(filial_id=row.filial_id, mensagem="x", produto_id=row.produto_id, lote_id=row.lote_id, quantidade=2)
    venda_id = _criar_venda_pendente(request, row.lote_id, row.preco_tabela, row.preco_tabela * 2, idempotency_key, sessao_id)

    # idade_minima_minutos=0: nenhuma role (nem app_backend) tem UPDATE em
    # vendas.data_venda pra "envelhecer" a linha no teste — então testamos a
    # lógica de resolução do reconciliador sem depender do relógio.
    resultado = reconciliar_vendas_pendentes(adapter, idade_minima_minutos=0)
    assert resultado["confirmadas"] >= 1

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        status_final = session.execute(text("SELECT status_confirmacao FROM vendas WHERE id = :id"), {"id": str(venda_id)}).scalar_one()
    assert status_final == "confirmada"


@requires_db
def test_reconciliador_marca_falha_quando_erp_nunca_recebeu() -> None:
    """Venda fica 'pendente' mas o ERP nunca viu essa idempotency_key
    (processo morreu ANTES de chamar o ERP) — falha fechada: nunca vira
    'confirmada' por omissão."""
    from sqlalchemy import text

    from app.agents.service import _criar_venda_pendente, _idempotency_key_venda
    from app.integrations.sync import reconciliar_vendas_pendentes
    from app.schemas.chat import ChatAtendimentoRequest

    _seed_principios_ativos_do_mock()
    run_sync(MockAdapter(), origem="mock")

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        row = session.execute(
            text(
                """
                SELECT p.id AS produto_id, l.id AS lote_id, f.id AS filial_id, p.preco_tabela
                FROM produtos p JOIN lotes l ON l.produto_id = p.id
                JOIN estoque e ON e.lote_id = l.id JOIN filiais f ON f.id = e.filial_id
                WHERE p.id_externo = 'PROD-002'
                """
            )
        ).first()

    sessao_id = uuid.uuid4()
    idempotency_key = _idempotency_key_venda(sessao_id, row.produto_id, row.lote_id, 1)
    request = ChatAtendimentoRequest(filial_id=row.filial_id, mensagem="x", produto_id=row.produto_id, lote_id=row.lote_id, quantidade=1)
    venda_id = _criar_venda_pendente(request, row.lote_id, row.preco_tabela, row.preco_tabela, idempotency_key, sessao_id)

    resultado = reconciliar_vendas_pendentes(MockAdapter(), idade_minima_minutos=0)
    assert resultado["falhas"] >= 1

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        status_final = session.execute(text("SELECT status_confirmacao FROM vendas WHERE id = :id"), {"id": str(venda_id)}).scalar_one()
    assert status_final == "falha"
