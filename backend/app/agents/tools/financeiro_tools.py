import uuid
from datetime import datetime, timezone
from decimal import Decimal

from crewai.tools import BaseTool
from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.agents.registry import agente_id_for
from app.models.enums import StatusAprovacaoEnum
from app.models.precificacao_historico import PrecificacaoHistorico


class CalcularMargemTool(BaseTool):
    name: str = "calcular_margem"
    description: str = (
        "Calcula a margem de lucro percentual de um preço proposto para um produto, "
        "usando o custo médio cadastrado. Recebe produto_id e preco_proposto. Use "
        "SEMPRE antes de aprovar um desconto — nunca aprove um preço com margem negativa "
        "sem justificativa explícita de estratégia (ex.: liquidar lote perto do vencimento)."
    )
    role: AgentRole = AgentRole.FINANCEIRO

    def _run(self, produto_id: str, preco_proposto: float) -> dict:
        with agent_session(self.role) as session:
            custo_medio = session.execute(
                text("SELECT custo_medio FROM produtos WHERE id = :id"), {"id": produto_id}
            ).scalar_one()

        if custo_medio is None:
            return {"custo_medio": None, "margem_percentual": None, "aviso": "produto sem custo_medio cadastrado"}

        custo = float(custo_medio)
        margem_percentual = round(((preco_proposto - custo) / preco_proposto) * 100, 2) if preco_proposto > 0 else None
        return {
            "custo_medio": custo,
            "preco_proposto": preco_proposto,
            "margem_percentual": margem_percentual,
            "margem_negativa": margem_percentual is not None and margem_percentual < 0,
        }


class AprovarOuRejeitarDescontoTool(BaseTool):
    name: str = "aprovar_ou_rejeitar_desconto"
    description: str = (
        "Finaliza uma proposta de desconto pendente (status='proposto'), aprovando ou "
        "rejeitando. Recebe precificacao_id, aprovar (true/false) e uma justificativa "
        "textual obrigatória com o raciocínio da decisão. Se aprovado e o desconto for "
        "geral de produto (não específico de um lote), atualiza também o preço de tabela."
    )
    role: AgentRole = AgentRole.FINANCEIRO

    def _run(self, precificacao_id: str, aprovar: bool, justificativa: str) -> dict:
        with agent_session(self.role) as session:
            proposta = session.get(PrecificacaoHistorico, uuid.UUID(precificacao_id))
            if proposta is None:
                return {"erro": "precificacao_id não encontrado"}
            if proposta.status_aprovacao.value != "proposto":
                return {"erro": f"proposta já está em status '{proposta.status_aprovacao.value}', não pode ser revisada de novo"}

            custo_medio = session.execute(
                text("SELECT custo_medio FROM produtos WHERE id = :id"), {"id": proposta.produto_id}
            ).scalar_one()
            margem_resultante = None
            if custo_medio and proposta.preco_novo > 0:
                margem_resultante = Decimal(
                    round(((float(proposta.preco_novo) - float(custo_medio)) / float(proposta.preco_novo)) * 100, 2)
                )

            proposta.status_aprovacao = StatusAprovacaoEnum.aprovado if aprovar else StatusAprovacaoEnum.rejeitado
            proposta.aprovado_por_agente_id = agente_id_for(self.role)
            proposta.aprovado_em = datetime.now(timezone.utc)
            proposta.margem_resultante = margem_resultante
            # motivo é campo do Gerente (proponente); a justificativa do Financeiro
            # já fica integralmente registrada em logs_auditoria via registrar_auditoria.

            if aprovar and proposta.lote_id is None:
                session.execute(
                    text("UPDATE produtos SET preco_tabela = :preco WHERE id = :id"),
                    {"preco": proposta.preco_novo, "id": proposta.produto_id},
                )

            session.flush()
            return {
                "precificacao_id": str(proposta.id),
                "status_aprovacao": proposta.status_aprovacao.value,
                "margem_resultante": float(margem_resultante) if margem_resultante is not None else None,
            }
