"""FASE 3 (BUG-01): fonte única de preço pra cobrança.

Sob a FASE 0 (F0-05), a aprovação do Agente Financeiro nunca escreve em
produtos.preco_tabela — ela é só uma RECOMENDAÇÃO persistida em
precificacao_historico (status_aprovacao='aprovado'). Precisava de alguém que
resolvesse "qual é o preço de verdade agora" a partir dessas recomendações, e
esse alguém é esta função — nunca um UPDATE direto na tabela de produtos.
"""

import uuid
from decimal import Decimal

from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session


def preco_efetivo(produto_id: uuid.UUID, lote_id: uuid.UUID) -> Decimal:
    """Resolve o preço de cobrança, nesta ordem:

    1. Desconto aprovado vigente para ESTE lote (mais específico).
    2. Desconto aprovado de PRODUTO (lote_id NULL na proposta — desconto geral).
    3. produtos.preco_tabela (nunca houve desconto aprovado).

    "Vigente" = a aprovação mais recente (aprovado_em DESC) — pode haver mais
    de uma linha 'aprovado' histórica pro mesmo lote/produto ao longo do
    tempo, a mais recente é a que vale.
    """
    with agent_session(AgentRole.ATENDENTE) as session:
        desconto_lote = session.execute(
            text(
                """
                SELECT preco_novo FROM precificacao_historico
                WHERE lote_id = :lote_id AND status_aprovacao = 'aprovado'
                ORDER BY aprovado_em DESC
                LIMIT 1
                """
            ),
            {"lote_id": str(lote_id)},
        ).scalar_one_or_none()
        if desconto_lote is not None:
            return desconto_lote

        desconto_produto = session.execute(
            text(
                """
                SELECT preco_novo FROM precificacao_historico
                WHERE produto_id = :produto_id AND lote_id IS NULL AND status_aprovacao = 'aprovado'
                ORDER BY aprovado_em DESC
                LIMIT 1
                """
            ),
            {"produto_id": str(produto_id)},
        ).scalar_one_or_none()
        if desconto_produto is not None:
            return desconto_produto

        return session.execute(
            text("SELECT preco_tabela FROM produtos WHERE id = :id"), {"id": str(produto_id)}
        ).scalar_one()
