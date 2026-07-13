import uuid
from decimal import Decimal

from crewai.tools import BaseTool
from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.agents.registry import agente_id_for
from app.models.precificacao_historico import PrecificacaoHistorico


class ConsultarEstoqueTool(BaseTool):
    name: str = "consultar_estoque"
    description: str = (
        "Consulta a posição de estoque atual de um produto em uma filial: quantidade "
        "disponível, lote e dias até o vencimento. Recebe produto_id e filial_id (UUIDs)."
    )
    role: AgentRole = AgentRole.GERENTE_ESTOQUE

    def _run(self, produto_id: str, filial_id: str) -> list[dict]:
        with agent_session(self.role) as session:
            rows = session.execute(
                text(
                    """
                    SELECT lote_id, numero_lote, data_validade, dias_para_vencer,
                           quantidade_atual, quantidade_reservada, quantidade_disponivel, status
                    FROM vw_estoque_atual
                    WHERE produto_id = :produto_id AND filial_id = :filial_id
                    ORDER BY dias_para_vencer ASC
                    """
                ),
                {"produto_id": produto_id, "filial_id": filial_id},
            )
            return [dict(row._mapping) for row in rows]


class AnalisarHistoricoVendasTool(BaseTool):
    name: str = "analisar_historico_vendas"
    description: str = (
        "Retorna o giro de vendas dos últimos 90 dias de um produto (unidades vendidas, "
        "número de vendas e receita), para calcular Sell-Through Rate e decidir sobre "
        "reposição ou desconto. Recebe produto_id (UUID)."
    )
    role: AgentRole = AgentRole.GERENTE_ESTOQUE

    def _run(self, produto_id: str) -> dict:
        with agent_session(self.role) as session:
            row = session.execute(
                text(
                    """
                    SELECT unidades_vendidas_90d, numero_vendas_90d, receita_90d
                    FROM vw_giro_estoque_90d
                    WHERE produto_id = :produto_id
                    """
                ),
                {"produto_id": produto_id},
            ).first()
            if row is None:
                return {"unidades_vendidas_90d": 0, "numero_vendas_90d": 0, "receita_90d": 0.0}
            data = dict(row._mapping)
            data["giro_diario_estimado"] = round(float(data["unidades_vendidas_90d"]) / 90, 3)
            return data


class ProdutosVencendoTool(BaseTool):
    name: str = "produtos_vencendo"
    description: str = (
        "Lista produtos com estoque disponível cuja validade vence dentro de N dias "
        "(padrão 60), já com preco_tabela e custo_medio incluídos — não é necessário "
        "buscar o preço em outra ferramenta. Ordenados do mais urgente para o menos "
        "urgente. Use isso para encontrar candidatos a desconto por proximidade de vencimento."
    )
    role: AgentRole = AgentRole.GERENTE_ESTOQUE

    def _run(self, dias: int = 60, filial_id: str | None = None) -> list[dict]:
        query = """
            SELECT e.produto_id, e.nome_comercial, e.filial_id, e.filial_nome, e.lote_id,
                   e.data_validade, e.dias_para_vencer, e.quantidade_disponivel,
                   p.preco_tabela, p.custo_medio
            FROM vw_estoque_atual e
            JOIN produtos p ON p.id = e.produto_id
            WHERE e.dias_para_vencer BETWEEN 0 AND :dias
              AND e.quantidade_disponivel > 0
        """
        params: dict[str, object] = {"dias": dias}
        if filial_id:
            query += " AND e.filial_id = :filial_id"
            params["filial_id"] = filial_id
        query += " ORDER BY e.dias_para_vencer ASC LIMIT 20"

        with agent_session(self.role) as session:
            rows = session.execute(text(query), params)
            return [dict(row._mapping) for row in rows]


class RegistrarPropostaDescontoTool(BaseTool):
    name: str = "registrar_proposta_desconto"
    description: str = (
        "Grava no banco uma PROPOSTA de desconto para um produto/lote (status='proposto'). "
        "Não altera o preço de venda — só o Agente Financeiro pode aprovar. Recebe "
        "produto_id, lote_id, preco_novo e um motivo textual claro (ex.: giro baixo + "
        "vencimento em 12 dias)."
    )
    role: AgentRole = AgentRole.GERENTE_ESTOQUE

    def _run(self, produto_id: str, lote_id: str, preco_novo: float, motivo: str) -> dict:
        with agent_session(self.role) as session:
            preco_atual = session.execute(
                text("SELECT preco_tabela FROM produtos WHERE id = :id"), {"id": produto_id}
            ).scalar_one()

            proposta = PrecificacaoHistorico(
                produto_id=uuid.UUID(produto_id),
                lote_id=uuid.UUID(lote_id),
                preco_anterior=preco_atual,
                preco_novo=Decimal(str(preco_novo)),
                motivo=motivo,
                proposto_por_agente_id=agente_id_for(self.role),
            )
            session.add(proposta)
            session.flush()
            return {
                "precificacao_id": str(proposta.id),
                "preco_anterior": float(preco_atual),
                "preco_novo": preco_novo,
                "status_aprovacao": "proposto",
            }
