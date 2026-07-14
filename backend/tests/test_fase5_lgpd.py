"""FASE 5 (LGPD): pseudonimização de dado clínico (LGPD-04), correção de
acesso a CPF (LGPD-02) e consentimento (LGPD-03). Mesma infraestrutura das
fases anteriores — precisa de TEST_DATABASE_URL com as migrations do Alembic
(0001-0003) aplicadas e credenciais de agente configuradas.
"""

import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.agents.audit import registrar_auditoria
from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.agents.pseudonimos import pseudonimo_id_for_cliente
from app.agents.service import _registrar_mensagem_sessao
from app.integrations.sync import _backend_session
from app.models.enums import TipoDecisaoEnum

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


def _criar_cliente_manual(*, consentimento: bool) -> uuid.UUID:
    session = _backend_session()
    try:
        cliente_id = session.execute(
            text(
                "INSERT INTO clientes (nome, consentimento_dado, consentimento_lgpd_em) "
                "VALUES (:nome, :consentimento, CASE WHEN :consentimento THEN now() ELSE NULL END) "
                "RETURNING id"
            ),
            {"nome": f"Cliente LGPD {uuid.uuid4().hex[:8]}", "consentimento": consentimento},
        ).scalar_one()
        session.commit()
    finally:
        session.close()
    return cliente_id


# ---------------------------------------------------------------------------
# LGPD-04: pseudonimos_titular só é acessível por app_backend — nenhuma role
# de agente lê nem escreve, nem a própria que "dono" seria o Atendente.
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.parametrize(
    "role", [AgentRole.ATENDENTE, AgentRole.GERENTE_ESTOQUE, AgentRole.FINANCEIRO, AgentRole.ORQUESTRADOR]
)
def test_nenhuma_role_de_agente_consegue_ler_pseudonimos_titular(role: AgentRole) -> None:
    with agent_session(role) as session:
        with pytest.raises(ProgrammingError, match="permission denied"):
            session.execute(text("SELECT pseudonimo_id FROM pseudonimos_titular LIMIT 1"))
        session.rollback()


# ---------------------------------------------------------------------------
# LGPD-02: agente_orquestrador tinha GRANT genérico demais (0011) dando
# acesso a clientes.cpf sem nenhum caso de uso — revogado na migration 0002.
# ---------------------------------------------------------------------------


@requires_db
def test_agente_orquestrador_nao_consegue_mais_ler_clientes() -> None:
    with agent_session(AgentRole.ORQUESTRADOR) as session:
        with pytest.raises(ProgrammingError, match="permission denied"):
            session.execute(text("SELECT cpf FROM clientes LIMIT 1"))
        session.rollback()


# ---------------------------------------------------------------------------
# LGPD-04: fluxo completo de eliminação — revoga o pseudônimo, preserva a
# auditoria, próxima sessão gera pseudônimo novo.
# ---------------------------------------------------------------------------


@requires_db
async def test_eliminar_dados_clinicos_revoga_pseudonimo_mas_preserva_auditoria(client: AsyncClient) -> None:
    cliente_id = _criar_cliente_manual(consentimento=True)
    pseudonimo_1 = pseudonimo_id_for_cliente(cliente_id)

    sessao_id = uuid.uuid4()
    log_id = registrar_auditoria(
        role=AgentRole.ATENDENTE,
        tipo_decisao=TipoDecisaoEnum.sugestao_similar,
        entidade_afetada="produtos",
        decisao_tomada="teste LGPD-04: sugestão registrada com pseudônimo",
        dados_base={"medicamentos_em_uso": ["losartana"]},
        sessao_id=sessao_id,
        pseudonimo_id=pseudonimo_1,
    )
    _registrar_mensagem_sessao(sessao_id, "cliente", "mensagem de teste LGPD-04", pseudonimo_id=pseudonimo_1)

    resp = await client.delete(f"/api/v1/clientes/{cliente_id}/dados-clinicos")
    assert resp.status_code == 204, resp.text

    session = _backend_session()
    try:
        pseudonimo_row = session.execute(
            text("SELECT cliente_id, revogado_em FROM pseudonimos_titular WHERE pseudonimo_id = :id"),
            {"id": str(pseudonimo_1)},
        ).first()
        assert pseudonimo_row is not None
        assert pseudonimo_row.cliente_id is None, "revogar tem que desligar cliente_id, não só carimbar revogado_em"
        assert pseudonimo_row.revogado_em is not None

        log_ainda_existe = session.execute(text("SELECT id FROM logs_auditoria WHERE id = :id"), {"id": str(log_id)}).first()
        assert log_ainda_existe is not None, "logs_auditoria é append-only — a revogação não pode apagar a linha"

        mensagem_ainda_existe = session.execute(
            text("SELECT id FROM sessoes_chat_mensagens WHERE sessao_id = :sid"), {"sid": str(sessao_id)}
        ).first()
        assert mensagem_ainda_existe is not None
    finally:
        session.close()

    # Nova "sessão" do mesmo cliente depois da revogação: pseudônimo NOVO,
    # nunca reaproveita o revogado.
    pseudonimo_2 = pseudonimo_id_for_cliente(cliente_id)
    assert pseudonimo_2 != pseudonimo_1


@requires_db
async def test_eliminar_dados_clinicos_de_cliente_sem_pseudonimo_e_204_idempotente(client: AsyncClient) -> None:
    """Cliente que nunca conversou com o Avatar não tem pseudônimo — revogar
    algo que não existe não é erro, é idempotente (0 linhas afetadas)."""
    cliente_id = _criar_cliente_manual(consentimento=True)
    resp = await client.delete(f"/api/v1/clientes/{cliente_id}/dados-clinicos")
    assert resp.status_code == 204, resp.text


@requires_db
async def test_eliminar_dados_clinicos_de_cliente_inexistente_e_404(client: AsyncClient) -> None:
    resp = await client.delete(f"/api/v1/clientes/{uuid.uuid4()}/dados-clinicos")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# LGPD-03: sem consentimento registrado, /chat/atendimento recusa com 403.
# Atendimento anônimo (sem cliente_id) nunca precisa de consentimento.
# ---------------------------------------------------------------------------


@requires_db
async def test_atendimento_com_cliente_id_sem_consentimento_retorna_403(client: AsyncClient) -> None:
    cliente_id = _criar_cliente_manual(consentimento=False)
    resp = await client.post(
        "/api/v1/chat/atendimento",
        json={"filial_id": str(uuid.uuid4()), "cliente_id": str(cliente_id), "mensagem": "teste LGPD-03"},
    )
    assert resp.status_code == 403, resp.text


@requires_db
async def test_atendimento_com_consentimento_registrado_nao_e_bloqueado_por_403(client: AsyncClient) -> None:
    cliente_id = _criar_cliente_manual(consentimento=True)
    resp = await client.post(
        "/api/v1/chat/atendimento",
        json={"filial_id": str(uuid.uuid4()), "cliente_id": str(cliente_id), "mensagem": "teste LGPD-03"},
    )
    assert resp.status_code != 403, resp.text


@requires_db
async def test_atendimento_anonimo_nao_exige_consentimento(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/chat/atendimento", json={"filial_id": str(uuid.uuid4()), "mensagem": "teste anônimo"}
    )
    assert resp.status_code != 403, resp.text


@requires_db
async def test_endpoint_consentimento_registra_data_e_flag(client: AsyncClient) -> None:
    cliente_id = _criar_cliente_manual(consentimento=False)
    resp = await client.post(f"/api/v1/clientes/{cliente_id}/consentimento")
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert corpo["consentimento_dado"] is True
    assert corpo["consentimento_lgpd_em"] is not None
