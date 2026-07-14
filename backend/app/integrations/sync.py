"""Sync worker (F0-03): puxa do ERPAdapter, normaliza e faz upsert no espelho
local por (origem, id_externo). Roda inteiramente síncrono (psycopg2), no
mesmo estilo de app/agents/db_sync.py, para não misturar sessão async
(app_backend/FastAPI) com sessão sync (agent_session) dentro da mesma função.

A regra mais importante deste arquivo: **falha fechada, nunca aberta**. Todo
dado vindo do ERP é tratado como não confiável (regra de engajamento #5). Se
não dá pra provar que um produto é MIP, ele vira tarja='vermelha'. Se um lote
não tem validade ou custo, ele é ignorado (nunca inserido com um valor
inventado). Erro de mapeamento é venda perdida, nunca risco clínico ou
financeiro — e todo caso assim é registrado em logs_auditoria via o agente
Orquestrador (o único papel com INSERT em logs_auditoria e leitura de tudo).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.audit import registrar_auditoria
from app.agents.config import AgentRole
from app.core.config import get_settings
from app.integrations.base import ERPAdapter
from app.models.enums import (
    FormaFarmaceuticaEnum,
    TarjaEnum,
    TipoDecisaoEnum,
    TipoMovimentacaoEnum,
    UnidadeConcentracaoEnum,
    ViaAdministracaoEnum,
)
from app.models.estoque import Estoque
from app.models.fabricante import Fabricante
from app.models.filial import Filial
from app.models.lote import Lote
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.models.principio_ativo import PrincipioAtivo
from app.models.produto import Produto

FORMAS_QUE_EXIGEM_PRINCIPIO_ATIVO = {
    FormaFarmaceuticaEnum.comprimido,
    FormaFarmaceuticaEnum.capsula,
    FormaFarmaceuticaEnum.xarope,
    FormaFarmaceuticaEnum.injetavel,
    FormaFarmaceuticaEnum.solucao,
    FormaFarmaceuticaEnum.suspensao,
}


@lru_cache
def _backend_sync_engine():
    """Engine síncrona (psycopg2) usando a MESMA credencial app_backend do
    core/db.py — só troca o driver, porque produtos/lotes/estoque/filiais
    (INSERT/UPDATE) já são GRANTs de app_backend desde a migration 0011.
    """
    settings = get_settings()
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    connect_args: dict[str, object] = (
        {"sslmode": "require"} if settings.db_ssl_require and sync_url.startswith("postgresql+psycopg2://") else {}
    )
    # FASE 1 (SEC-12): pool pequeno de propósito — este engine só serve o sync
    # worker e o reconciliador, processos batch/periódicos, não uma rota HTTP
    # sob rate limit. Não precisa da mesma folga dos engines de agente em
    # app/agents/db_sync.py.
    return create_engine(sync_url, pool_pre_ping=True, connect_args=connect_args, future=True, pool_size=5, max_overflow=5)


@lru_cache
def _backend_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=_backend_sync_engine(), expire_on_commit=False)


def _backend_session() -> Session:
    return _backend_session_factory()()


@dataclass
class SyncStats:
    filiais_sincronizadas: int = 0
    produtos_sincronizados: int = 0
    produtos_ignorados: int = 0
    lotes_sincronizados: int = 0
    lotes_ignorados: int = 0
    estoque_sincronizado: int = 0
    eventos_falha_fechada: list[str] = field(default_factory=list)


def _log_falha_fechada(
    *, tipo_decisao: TipoDecisaoEnum, entidade_afetada: str, entidade_id: uuid.UUID | None, mensagem: str, dados_base: dict
) -> None:
    registrar_auditoria(
        role=AgentRole.ORQUESTRADOR,
        tipo_decisao=tipo_decisao,
        entidade_afetada=entidade_afetada,
        entidade_id=entidade_id,
        decisao_tomada=mensagem,
        dados_base=dados_base,
        justificativa="Sync worker (F0-03): falha fechada — dado do ERP não confiável o suficiente para aplicar sem registro.",
    )


def _mapear_tarja(tarja_raw: str | None) -> tuple[TarjaEnum, bool]:
    """Regra inegociável: se não dá pra PROVAR que é MIP, vira 'vermelha'.

    Retorna (tarja, foi_fail_closed). Nunca ajuste esta função para "resolver"
    uma taxa de conversão ruim no MockAdapter — o problema nesse caso é o
    mapeamento (ou o cadastro do ERP), nunca a regra em si.
    """
    if tarja_raw is None:
        return TarjaEnum.vermelha, True
    normalizado = tarja_raw.strip().lower()
    for tarja in TarjaEnum:
        if tarja.value == normalizado:
            return tarja, False
    return TarjaEnum.vermelha, True


def _mapear_enum(enum_cls: type, valor_raw: str | None):
    if valor_raw is None:
        return None
    normalizado = valor_raw.strip().lower()
    for membro in enum_cls:
        if membro.value == normalizado:
            return membro
    return None


def _resolver_fabricante(session: Session, nome: str | None) -> uuid.UUID | None:
    if not nome:
        return None
    fabricante = session.execute(select(Fabricante).where(Fabricante.nome == nome)).scalars().first()
    if fabricante is None:
        fabricante = Fabricante(nome=nome)
        session.add(fabricante)
        session.flush()
    return fabricante.id


def _resolver_principio_ativo(session: Session, nome: str | None) -> uuid.UUID | None:
    """Nunca cria um princípio ativo novo: curadoria de conteúdo clínico é
    trabalho humano (mesma regra já aplicada a bulas/interações — migration
    0004), não algo que o sync deva inventar a partir do nome vindo do ERP.
    """
    if not nome:
        return None
    principio = session.execute(select(PrincipioAtivo).where(PrincipioAtivo.nome == nome)).scalars().first()
    return principio.id if principio else None


def sync_filiais(adapter: ERPAdapter, origem: str, session: Session) -> int:
    count = 0
    for fe in adapter.listar_filiais():
        filial = session.execute(select(Filial).where(Filial.origem == origem, Filial.id_externo == fe.id_externo)).scalars().first()
        if filial is None:
            filial = Filial(origem=origem, id_externo=fe.id_externo)
            session.add(filial)
        filial.nome = fe.nome
        filial.cnpj = fe.cnpj
        filial.endereco = fe.endereco
        filial.cidade = fe.cidade
        filial.uf = fe.uf
        filial.ativo = fe.ativo
        filial.sincronizado_em = datetime.now(timezone.utc)
        session.flush()
        count += 1
    return count


def sync_produtos(adapter: ERPAdapter, origem: str, session: Session, stats: SyncStats) -> None:
    for pe in adapter.listar_produtos():
        tarja, tarja_fail_closed = _mapear_tarja(pe.tarja_raw)
        fabricante_id = _resolver_fabricante(session, pe.fabricante_nome)
        principio_ativo_id = _resolver_principio_ativo(session, pe.principio_ativo_nome)
        forma = _mapear_enum(FormaFarmaceuticaEnum, pe.forma_farmaceutica_raw)
        via = _mapear_enum(ViaAdministracaoEnum, pe.via_administracao_raw)
        unidade = _mapear_enum(UnidadeConcentracaoEnum, pe.concentracao_unidade_raw)

        dados_incompletos = (
            fabricante_id is None
            or forma is None
            or via is None
            or unidade is None
            or pe.preco_tabela is None
            or pe.concentracao_valor is None
            or pe.quantidade_embalagem is None
        )
        exige_principio_sem_ter = forma in FORMAS_QUE_EXIGEM_PRINCIPIO_ATIVO and principio_ativo_id is None

        if dados_incompletos or exige_principio_sem_ter:
            stats.produtos_ignorados += 1
            motivo = "dado obrigatório ausente/não mapeável" if dados_incompletos else "princípio ativo não cadastrado localmente"
            stats.eventos_falha_fechada.append(f"produto id_externo={pe.id_externo} ignorado: {motivo}")
            _log_falha_fechada(
                tipo_decisao=TipoDecisaoEnum.alerta_estoque,
                entidade_afetada="produtos",
                entidade_id=None,
                mensagem=f"Produto '{pe.nome_comercial}' (id_externo={pe.id_externo}) do ERP '{origem}' não sincronizado: {motivo}.",
                dados_base={"id_externo": pe.id_externo, "origem": origem, "produto_externo": pe.model_dump(mode="json")},
            )
            continue

        produto = session.execute(select(Produto).where(Produto.origem == origem, Produto.id_externo == pe.id_externo)).scalars().first()
        eh_novo = produto is None
        if produto is None:
            produto = Produto(origem=origem, id_externo=pe.id_externo, fabricante_id=fabricante_id)
            session.add(produto)

        produto.fabricante_id = fabricante_id
        produto.principio_ativo_id = principio_ativo_id
        produto.nome_comercial = pe.nome_comercial
        produto.codigo_barras = pe.codigo_barras
        produto.registro_anvisa = pe.registro_anvisa
        produto.forma_farmaceutica = forma
        produto.via_administracao = via
        produto.concentracao_valor = pe.concentracao_valor
        produto.concentracao_unidade = unidade
        produto.quantidade_embalagem = pe.quantidade_embalagem
        produto.tarja = tarja
        produto.preco_tabela = pe.preco_tabela
        produto.custo_medio = pe.custo_medio
        produto.ativo = pe.ativo
        produto.sincronizado_em = datetime.now(timezone.utc)
        session.flush()
        stats.produtos_sincronizados += 1

        if tarja_fail_closed:
            stats.eventos_falha_fechada.append(f"produto id_externo={pe.id_externo} com tarja não mapeável (raw={pe.tarja_raw!r}) -> 'vermelha'")
            _log_falha_fechada(
                tipo_decisao=TipoDecisaoEnum.alerta_estoque,
                entidade_afetada="produtos",
                entidade_id=produto.id,
                mensagem=(
                    f"Produto '{pe.nome_comercial}' (id_externo={pe.id_externo}) do ERP '{origem}' com tarja "
                    f"não mapeável (raw={pe.tarja_raw!r}) — gravado como tarja='vermelha' por falha fechada, "
                    "ficando invisível ao agente atendente até curadoria manual."
                ),
                dados_base={"id_externo": pe.id_externo, "origem": origem, "tarja_raw": pe.tarja_raw, "novo_registro": eh_novo},
            )


def sync_lotes(adapter: ERPAdapter, origem: str, session: Session, stats: SyncStats) -> None:
    for le in adapter.listar_lotes():
        produto = session.execute(
            select(Produto).where(Produto.origem == origem, Produto.id_externo == le.produto_id_externo)
        ).scalars().first()

        dados_ok = (
            produto is not None
            and le.data_validade is not None
            and le.data_fabricacao is not None
            and le.custo_unitario is not None
            and le.quantidade_recebida is not None
            and (le.data_fabricacao is None or le.data_validade > le.data_fabricacao)
        )
        if not dados_ok:
            stats.lotes_ignorados += 1
            motivo = (
                "produto ainda não sincronizado" if produto is None
                else "data_validade ausente" if le.data_validade is None
                else "data_fabricacao ausente" if le.data_fabricacao is None
                else "custo_unitario ausente" if le.custo_unitario is None
                else "quantidade_recebida ausente" if le.quantidade_recebida is None
                else "data_validade não é posterior à data_fabricacao"
            )
            stats.eventos_falha_fechada.append(f"lote id_externo={le.id_externo} ignorado: {motivo}")
            _log_falha_fechada(
                tipo_decisao=TipoDecisaoEnum.alerta_estoque,
                entidade_afetada="lotes",
                entidade_id=None,
                mensagem=f"Lote '{le.numero_lote}' (id_externo={le.id_externo}) do ERP '{origem}' não sincronizado: {motivo}.",
                dados_base={"id_externo": le.id_externo, "origem": origem, "lote_externo": le.model_dump(mode="json")},
            )
            continue

        lote = session.execute(select(Lote).where(Lote.origem == origem, Lote.id_externo == le.id_externo)).scalars().first()
        if lote is None:
            lote = Lote(origem=origem, id_externo=le.id_externo, produto_id=produto.id, data_fabricacao=le.data_fabricacao)
            session.add(lote)

        lote.produto_id = produto.id
        lote.numero_lote = le.numero_lote
        lote.data_fabricacao = le.data_fabricacao
        lote.data_validade = le.data_validade
        lote.quantidade_recebida = le.quantidade_recebida
        lote.custo_unitario = le.custo_unitario
        lote.sincronizado_em = datetime.now(timezone.utc)
        session.flush()
        stats.lotes_sincronizados += 1


def sync_estoque(adapter: ERPAdapter, origem: str, session: Session, stats: SyncStats) -> None:
    """Toda mudança de quantidade_atual grava um lançamento em
    movimentacoes_estoque (tipo='sincronizacao_erp'). Sem isso o sync seria o
    único dos três caminhos de escrita (venda, movimentação manual, sync) que
    pula o ledger — e o ledger deixa de ser uma história completa do saldo,
    impossibilitando reconciliação de verdade.
    """
    for ee in adapter.listar_estoque():
        filial = session.execute(select(Filial).where(Filial.origem == origem, Filial.id_externo == ee.filial_id_externa)).scalars().first()
        lote = session.execute(select(Lote).where(Lote.origem == origem, Lote.id_externo == ee.lote_id_externo)).scalars().first()
        if filial is None or lote is None:
            stats.eventos_falha_fechada.append(
                f"estoque produto_id_externo={ee.produto_id_externo}/lote_id_externo={ee.lote_id_externo} ignorado: filial ou lote não sincronizado"
            )
            continue

        quantidade_atual = ee.quantidade_atual
        if quantidade_atual < 0:
            # HOSTIL: ERP mandou estoque negativo. Falha fechada = zero, nunca
            # um número negativo que quebraria o CHECK local ou inflaria
            # "disponível" por engano de sinal.
            stats.eventos_falha_fechada.append(
                f"estoque produto_id_externo={ee.produto_id_externo}/lote_id_externo={ee.lote_id_externo} com quantidade negativa ({ee.quantidade_atual}) do ERP -> clampado para 0"
            )
            _log_falha_fechada(
                tipo_decisao=TipoDecisaoEnum.alerta_estoque,
                entidade_afetada="estoque",
                entidade_id=None,
                mensagem=(
                    f"ERP '{origem}' reportou quantidade_atual negativa ({ee.quantidade_atual}) para "
                    f"produto_id_externo={ee.produto_id_externo}/lote_id_externo={ee.lote_id_externo} — clampado para 0."
                ),
                dados_base={"origem": origem, "estoque_externo": ee.model_dump(mode="json")},
            )
            quantidade_atual = 0

        estoque = session.execute(
            select(Estoque).where(Estoque.filial_id == filial.id, Estoque.lote_id == lote.id)
        ).scalars().first()

        quantidade_antes = 0
        if estoque is None:
            estoque = Estoque(origem=origem, id_externo=f"{ee.lote_id_externo}:{ee.filial_id_externa}", filial_id=filial.id, lote_id=lote.id)
            session.add(estoque)
            session.flush()  # precisa do id gerado pra referenciar em movimentacoes_estoque
        else:
            quantidade_antes = estoque.quantidade_atual
            if quantidade_antes != quantidade_atual:
                # F0-07: o ERP sempre ganha. Divergência do espelho é corrigida
                # e registrada em logs_auditoria — nunca silenciosamente
                # sobrescrita sem rastro.
                _log_falha_fechada(
                    tipo_decisao=TipoDecisaoEnum.alerta_estoque,
                    entidade_afetada="estoque",
                    entidade_id=estoque.id,
                    mensagem=(
                        f"Reconciliação: espelho tinha quantidade_atual={quantidade_antes}, ERP '{origem}' "
                        f"diz {quantidade_atual}. O ERP é a fonte da verdade — espelho corrigido."
                    ),
                    dados_base={"quantidade_local_antes": quantidade_antes, "quantidade_erp": quantidade_atual, "origem": origem},
                )

        delta = quantidade_atual - quantidade_antes
        if delta != 0:
            session.add(
                MovimentacaoEstoque(
                    estoque_id=estoque.id,
                    tipo=TipoMovimentacaoEnum.sincronizacao_erp,
                    quantidade_delta=delta,
                    quantidade_resultante=quantidade_atual,
                    motivo=f"Sincronização com ERP '{origem}' (produto_id_externo={ee.produto_id_externo}, lote_id_externo={ee.lote_id_externo})",
                )
            )

        estoque.quantidade_atual = quantidade_atual
        estoque.quantidade_reservada = min(ee.quantidade_reservada, quantidade_atual)
        estoque.sincronizado_em = datetime.now(timezone.utc)
        session.flush()
        stats.estoque_sincronizado += 1


def run_sync(adapter: ERPAdapter, origem: str) -> SyncStats:
    """Ponto de entrada único do sync worker. Ordem importa: filiais e
    produtos precisam existir antes de lotes; lotes antes de estoque.
    """
    stats = SyncStats()
    session = _backend_session()
    try:
        stats.filiais_sincronizadas = sync_filiais(adapter, origem, session)
        sync_produtos(adapter, origem, session, stats)
        sync_lotes(adapter, origem, session, stats)
        sync_estoque(adapter, origem, session, stats)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return stats


def reconciliar_vendas_pendentes(adapter: ERPAdapter, idade_minima_minutos: int = 5) -> dict[str, int]:
    """Outbox: varre vendas 'pendente' mais antigas que idade_minima_minutos,
    reconsulta o ERP pela idempotency_key e resolve.

    Roda com duas identidades de propósito: leitura ampla via ORQUESTRADOR
    (única role com visão de tudo) e escrita via ATENDENTE (única role com
    UPDATE em vendas.status_confirmacao e no débito de estoque) — o
    Orquestrador nunca escreve dado operacional diretamente, só decide e
    audita (regra já estabelecida em 0011).
    """
    from sqlalchemy import text as sqltext

    from app.agents.db_sync import agent_session
    from app.agents.service import _debitar_estoque_venda, _marcar_venda_confirmada, _marcar_venda_falha

    resultados = {"confirmadas": 0, "falhas": 0, "ainda_pendentes": 0}

    with agent_session(AgentRole.ORQUESTRADOR) as session:
        pendentes = session.execute(
            sqltext(
                """
                SELECT id, idempotency_key, filial_id
                FROM vendas
                WHERE status_confirmacao = 'pendente'
                  AND idempotency_key IS NOT NULL
                  AND data_venda < now() - (:minutos || ' minutes')::interval
                """
            ),
            {"minutos": idade_minima_minutos},
        ).all()

    for venda_id, idempotency_key, filial_id in pendentes:
        with agent_session(AgentRole.ORQUESTRADOR) as session:
            item = session.execute(
                sqltext(
                    """
                    SELECT vi.quantidade, p.origem AS produto_origem, l.origem AS lote_origem,
                           f.origem AS filial_origem, e.id AS estoque_id
                    FROM vendas_itens vi
                    JOIN produtos p ON p.id = vi.produto_id
                    JOIN lotes l ON l.id = vi.lote_id
                    JOIN filiais f ON f.id = :filial_id
                    JOIN estoque e ON e.lote_id = vi.lote_id AND e.filial_id = f.id
                    WHERE vi.venda_id = :venda_id
                    LIMIT 1
                    """
                ),
                {"venda_id": str(venda_id), "filial_id": str(filial_id)},
            ).first()

        eh_venda_via_erp = bool(
            item and item.produto_origem != "manual" and item.lote_origem != "manual" and item.filial_origem != "manual"
        )

        if not eh_venda_via_erp:
            # Sem ERP pra perguntar "essa venda entrou?" — falha fechada:
            # depois do timeout, nunca vira 'confirmada' por omissão.
            _marcar_venda_falha(venda_id, "Reconciliador: sem ERP associado e pendente além do timeout — falha fechada.")
            resultados["falhas"] += 1
            continue

        try:
            confirmada = adapter.consultar_venda_por_idempotency_key(idempotency_key)
        except Exception:
            resultados["ainda_pendentes"] += 1
            continue

        if confirmada is not None:
            if item is not None:
                _debitar_estoque_venda(
                    item.estoque_id,
                    item.quantidade,
                    venda_id,
                    f"Reconciliação: venda confirmada no ERP (id_externo={confirmada.id_externo})",
                    exigir_disponibilidade=False,
                )
            _marcar_venda_confirmada(venda_id)
            resultados["confirmadas"] += 1
        else:
            _marcar_venda_falha(venda_id, "Reconciliador: ERP não reconhece a idempotency_key — a venda nunca chegou lá.")
            resultados["falhas"] += 1

    return resultados
