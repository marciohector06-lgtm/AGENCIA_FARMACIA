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


def _custo_indisponivel(custo: Decimal | None) -> bool:
    return custo is None or custo <= 0


class CalcularMargemTool(BaseTool):
    name: str = "calcular_margem"
    description: str = (
        "Calcula a margem de lucro percentual de um preço proposto para um LOTE específico, "
        "usando o custo do lote (lotes.custo_unitario — vem do ERP via sync; "
        "produtos.custo_medio está DEPRECADO, esta tool nunca lê de lá). Recebe lote_id e "
        "preco_proposto. Se o lote não tiver custo cadastrado (NULL ou zero), devolve "
        "{'erro': 'custo_indisponivel'} — nesse caso NUNCA aprove o desconto; rejeite com "
        "justificativa citando a necessidade de revisão manual do custo."
    )
    role: AgentRole = AgentRole.FINANCEIRO

    def _run(self, lote_id: str, preco_proposto: float) -> dict:
        # BUG-08: converte pra Decimal na fronteira de entrada (a LLM só fala
        # JSON/float) e nunca mais volta a float até o dict de retorno — todo
        # o cálculo de margem roda em Decimal.
        preco = Decimal(str(preco_proposto))

        with agent_session(self.role) as session:
            custo_unitario = session.execute(
                text("SELECT custo_unitario FROM lotes WHERE id = :id"), {"id": lote_id}
            ).scalar_one_or_none()

        if _custo_indisponivel(custo_unitario):
            # BUG-06: nunca aprovação no escuro. Erro estruturado, não um
            # número inventado — aprovar_ou_rejeitar_desconto também recusa
            # a aprovação de forma determinística se isso for ignorado.
            return {
                "erro": "custo_indisponivel",
                "aviso": "Lote sem custo cadastrado (NULL ou zero) — não aprove; recomende revisão manual.",
            }

        margem_percentual: Decimal | None = None
        if preco > 0:
            margem_percentual = ((preco - custo_unitario) / preco * 100).quantize(Decimal("0.01"))

        return {
            "custo_unitario": float(custo_unitario),
            "preco_proposto": float(preco),
            "margem_percentual": float(margem_percentual) if margem_percentual is not None else None,
            "margem_negativa": margem_percentual is not None and margem_percentual < 0,
        }


class AprovarOuRejeitarDescontoTool(BaseTool):
    name: str = "aprovar_ou_rejeitar_desconto"
    description: str = (
        "Finaliza uma proposta de desconto pendente (status='proposto'), aprovando ou "
        "rejeitando. Recebe precificacao_id, aprovar (true/false) e uma justificativa "
        "textual obrigatória com o raciocínio da decisão. Aprovar NÃO altera o preço de "
        "tabela do produto — é uma recomendação persistida (status_aprovacao='aprovado') "
        "que passa a valer na cobrança através de preco_efetivo(). Se o custo do lote "
        "estiver indisponível, a aprovação é recusada automaticamente (vira rejeição), "
        "mesmo que aprovar=true tenha sido pedido — nunca aprovação no escuro."
    )
    role: AgentRole = AgentRole.FINANCEIRO

    def _run(self, precificacao_id: str, aprovar: bool, justificativa: str) -> dict:
        with agent_session(self.role) as session:
            proposta = session.get(PrecificacaoHistorico, uuid.UUID(precificacao_id))
            if proposta is None:
                return {"erro": "precificacao_id não encontrado"}
            if proposta.status_aprovacao.value != "proposto":
                return {"erro": f"proposta já está em status '{proposta.status_aprovacao.value}', não pode ser revisada de novo"}

            # BUG-06: custo vem do LOTE da proposta (lotes.custo_unitario),
            # nunca de produtos.custo_medio (deprecado). Se a proposta não tem
            # lote (desconto geral de produto, caso hoje não gerado por
            # nenhuma tool mas suportado pelo schema), não há lote pra tirar
            # custo — tratado como custo indisponível também, pela mesma regra.
            custo_unitario: Decimal | None = None
            if proposta.lote_id is not None:
                custo_unitario = session.execute(
                    text("SELECT custo_unitario FROM lotes WHERE id = :id"), {"id": proposta.lote_id}
                ).scalar_one_or_none()

            custo_indisponivel = _custo_indisponivel(custo_unitario)

            if aprovar and custo_indisponivel:
                # Determinístico: nunca confia no LLM pra não aprovar no
                # escuro — mesmo que ele tenha pedido aprovar=true, a
                # ferramenta recusa e força rejeição. Fica registrado no
                # log de auditoria (via registrar_auditoria, camada acima)
                # que a decisão real foi "rejeitado", não "aprovado".
                proposta.status_aprovacao = StatusAprovacaoEnum.rejeitado
                proposta.aprovado_por_agente_id = agente_id_for(self.role)
                proposta.aprovado_em = datetime.now(timezone.utc)
                proposta.margem_resultante = None
                session.flush()
                return {
                    "precificacao_id": str(proposta.id),
                    "status_aprovacao": "rejeitado",
                    "margem_resultante": None,
                    "erro": "custo_indisponivel",
                    "aviso": (
                        "Aprovação recusada automaticamente: custo do lote indisponível (NULL, zero, ou "
                        "proposta sem lote). Proposta marcada como rejeitada — necessária revisão manual "
                        "do custo antes de qualquer nova proposta para este lote."
                    ),
                }

            margem_resultante: Decimal | None = None
            if not custo_indisponivel and proposta.preco_novo > 0:
                # BUG-08b: tudo em Decimal — o bug original passava por float
                # no meio do cálculo (Decimal(round(float(...), 2)) sem str()),
                # que introduz erro de ponto flutuante bem na hora de decidir
                # dinheiro. custo_unitario e preco_novo já são Decimal (colunas
                # Numeric); nunca precisam de float() pra fazer conta.
                margem_calculada = ((proposta.preco_novo - custo_unitario) / proposta.preco_novo * 100).quantize(Decimal("0.01"))
                # BUG-05: clamp defensivo antes do INSERT — preco_novo muito
                # baixo perto de um custo alto (ex.: liquidação de lote perto
                # do vencimento) pode gerar uma margem teoricamente extrema;
                # NUMERIC(7,2) (migration 0024) comporta até ±99999,99, mas o
                # clamp aqui é mais conservador de propósito.
                margem_resultante = max(Decimal("-9999.99"), min(Decimal("9999.99"), margem_calculada))

            proposta.status_aprovacao = StatusAprovacaoEnum.aprovado if aprovar else StatusAprovacaoEnum.rejeitado
            proposta.aprovado_por_agente_id = agente_id_for(self.role)
            proposta.aprovado_em = datetime.now(timezone.utc)
            proposta.margem_resultante = margem_resultante
            # motivo é campo do Gerente (proponente); a justificativa do Financeiro
            # já fica integralmente registrada em logs_auditoria via registrar_auditoria.

            # BUG-01 (sob F0-05): NUNCA escreve em produtos.preco_tabela aqui.
            # A aprovação é só a recomendação persistida acima
            # (status_aprovacao='aprovado') — quem resolve o preço de
            # cobrança de verdade é app/agents/pricing.py::preco_efetivo,
            # lido no momento da venda, nunca por um UPDATE direto que fingia
            # que este sistema é dono do preço.

            session.flush()
            return {
                "precificacao_id": str(proposta.id),
                "status_aprovacao": proposta.status_aprovacao.value,
                "margem_resultante": float(margem_resultante) if margem_resultante is not None else None,
            }
