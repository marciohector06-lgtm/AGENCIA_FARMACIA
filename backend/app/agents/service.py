"""Camada de orquestração: monta Agents/Tasks/Crews do CrewAI e garante que toda
decisão autônoma seja persistida de forma determinística (nunca depende do LLM
"lembrar" de chamar uma ferramenta de auditoria).
"""

import uuid
from decimal import Decimal
from typing import Any

from crewai import Crew, Process, Task
from sqlalchemy import text

from app.agents.agents_def import build_agente_atendente, build_agente_financeiro, build_agente_gerente_estoque
from app.agents.audit import registrar_auditoria
from app.agents.config import AgentRole
from app.agents.db_sync import agent_session
from app.agents.llm import build_llm
from app.agents.registry import agente_id_for
from app.agents.schemas import (
    AnaliseEstoqueFinanceiroOutput,
    AnaliseEstoqueGerenteOutput,
    ConfirmacaoCompraOutput,
    RespostaAtendimentoOutput,
)
from app.models.enums import CanalVendaEnum, TipoDecisaoEnum
from app.models.venda import Venda, VendaItem
from app.schemas.agentes import AnaliseEstoqueResponse, DecisaoPrecificacaoResumo
from app.schemas.chat import ChatAtendimentoRequest, ChatAtendimentoResponse, ProdutoSugeridoResponse


def run_analise_estoque(filial_id: uuid.UUID | None, dias_vencimento: int = 60) -> AnaliseEstoqueResponse:
    log_ids: list[uuid.UUID] = []

    # --- Etapa 1: Gerente de Estoque identifica candidatos e propõe descontos ---
    agente_gerente = build_agente_gerente_estoque(build_llm(temperature=0.2))
    filtro_filial = f", usando filial_id={filial_id}" if filial_id else " (todas as filiais)"
    task_gerente = Task(
        description=(
            f"Use a ferramenta produtos_vencendo com dias={dias_vencimento}{filtro_filial} para achar "
            "candidatos. Para CADA candidato relevante, use analisar_historico_vendas para embasar sua "
            "decisão com dados reais antes de decidir se um desconto é necessário e de qual tamanho. "
            "Registre cada proposta necessária com registrar_proposta_desconto. Se nenhum candidato "
            "precisar de desconto, não registre nada e explique por quê no resumo."
        ),
        expected_output=(
            "Lista de todas as propostas efetivamente registradas via registrar_proposta_desconto "
            "(produto_id, produto_nome, lote_id, precificacao_id, preco_anterior, preco_novo, motivo) "
            "mais um resumo textual do raciocínio."
        ),
        agent=agente_gerente,
        output_pydantic=AnaliseEstoqueGerenteOutput,
    )
    crew_gerente = Crew(agents=[agente_gerente], tasks=[task_gerente], process=Process.sequential, verbose=True)
    resultado_gerente = crew_gerente.kickoff()
    saida_gerente: AnaliseEstoqueGerenteOutput = resultado_gerente.pydantic  # type: ignore[assignment]

    for proposta in saida_gerente.propostas:
        log_id = registrar_auditoria(
            role=AgentRole.GERENTE_ESTOQUE,
            tipo_decisao=TipoDecisaoEnum.ajuste_preco,
            entidade_afetada="precificacao_historico",
            entidade_id=uuid.UUID(proposta.precificacao_id),
            decisao_tomada=f"Proposta de desconto: R${proposta.preco_anterior} -> R${proposta.preco_novo}",
            dados_base=proposta.model_dump(),
            justificativa=proposta.motivo,
        )
        log_ids.append(log_id)

    if not saida_gerente.propostas:
        resumo_final = f"Nenhuma proposta de desconto necessária. {saida_gerente.resumo}"
        log_ids.append(
            registrar_auditoria(
                role=AgentRole.ORQUESTRADOR,
                tipo_decisao=TipoDecisaoEnum.recomendacao_giro,
                entidade_afetada="precificacao_historico",
                decisao_tomada=resumo_final,
                dados_base={"dias_vencimento": dias_vencimento, "filial_id": str(filial_id) if filial_id else None},
            )
        )
        return AnaliseEstoqueResponse(
            propostas_geradas=0,
            aprovadas=0,
            rejeitadas=0,
            decisoes=[],
            resumo=resumo_final,
            log_auditoria_ids=log_ids,
        )

    # --- Etapa 2: Financeiro revisa e aprova/rejeita cada proposta ---
    agente_financeiro = build_agente_financeiro(build_llm(temperature=0.1))
    ids_para_revisar = ", ".join(p.precificacao_id for p in saida_gerente.propostas)
    task_financeiro = Task(
        description=(
            f"Revise EXATAMENTE estas propostas de desconto pendentes (precificacao_id): {ids_para_revisar}. "
            f"Contexto completo enviado pelo Gerente de Estoque: {saida_gerente.model_dump_json()}. "
            "Para cada uma, calcule a margem com calcular_margem (produto_id e preco_novo estão no contexto) "
            "e decida aprovar ou rejeitar com aprovar_ou_rejeitar_desconto, sempre com justificativa."
        ),
        expected_output="Lista de decisões (precificacao_id, aprovado, margem_resultante, justificativa) e um resumo.",
        agent=agente_financeiro,
        output_pydantic=AnaliseEstoqueFinanceiroOutput,
    )
    crew_financeiro = Crew(agents=[agente_financeiro], tasks=[task_financeiro], process=Process.sequential, verbose=True)
    resultado_financeiro = crew_financeiro.kickoff()
    saida_financeiro: AnaliseEstoqueFinanceiroOutput = resultado_financeiro.pydantic  # type: ignore[assignment]

    for decisao in saida_financeiro.decisoes:
        log_id = registrar_auditoria(
            role=AgentRole.FINANCEIRO,
            tipo_decisao=TipoDecisaoEnum.ajuste_preco,
            entidade_afetada="precificacao_historico",
            entidade_id=uuid.UUID(decisao.precificacao_id),
            decisao_tomada="aprovado" if decisao.aprovado else "rejeitado",
            dados_base=decisao.model_dump(),
            justificativa=decisao.justificativa,
            confianca=None,
        )
        log_ids.append(log_id)

    aprovadas = sum(1 for d in saida_financeiro.decisoes if d.aprovado)
    rejeitadas = len(saida_financeiro.decisoes) - aprovadas

    resumo_final = (
        f"{len(saida_gerente.propostas)} proposta(s) analisada(s): {aprovadas} aprovada(s), "
        f"{rejeitadas} rejeitada(s). {saida_financeiro.resumo}"
    )
    log_ids.append(
        registrar_auditoria(
            role=AgentRole.ORQUESTRADOR,
            tipo_decisao=TipoDecisaoEnum.resolucao_conflito,
            entidade_afetada="precificacao_historico",
            decisao_tomada=resumo_final,
            dados_base={
                "propostas": [p.model_dump() for p in saida_gerente.propostas],
                "decisoes": [d.model_dump() for d in saida_financeiro.decisoes],
            },
        )
    )

    decisoes_resumo = [
        DecisaoPrecificacaoResumo(
            precificacao_id=uuid.UUID(d.precificacao_id),
            aprovado=d.aprovado,
            margem_resultante=d.margem_resultante,
            justificativa=d.justificativa,
        )
        for d in saida_financeiro.decisoes
    ]

    return AnaliseEstoqueResponse(
        propostas_geradas=len(saida_gerente.propostas),
        aprovadas=aprovadas,
        rejeitadas=rejeitadas,
        decisoes=decisoes_resumo,
        resumo=resumo_final,
        log_auditoria_ids=log_ids,
    )


def _buscar_produto_basico(produto_id: uuid.UUID) -> dict[str, Any] | None:
    with agent_session(AgentRole.ATENDENTE) as session:
        row = session.execute(
            text("SELECT id, nome_comercial, preco_tabela FROM produtos WHERE id = :id"),
            {"id": str(produto_id)},
        ).first()
        return dict(row._mapping) if row else None


def _buscar_lote_disponivel(produto_id: uuid.UUID, filial_id: uuid.UUID) -> uuid.UUID | None:
    with agent_session(AgentRole.ATENDENTE) as session:
        row = session.execute(
            text(
                """
                SELECT lote_id FROM vw_estoque_atual
                WHERE produto_id = :produto_id AND filial_id = :filial_id AND quantidade_disponivel > 0
                ORDER BY dias_para_vencer ASC
                LIMIT 1
                """
            ),
            {"produto_id": str(produto_id), "filial_id": str(filial_id)},
        ).first()
        return row.lote_id if row else None


def run_atendimento(request: ChatAtendimentoRequest) -> ChatAtendimentoResponse:
    sessao_id = request.sessao_id or uuid.uuid4()

    if not request.confirmar_compra:
        return _run_atendimento_pesquisa(request, sessao_id)
    return _run_atendimento_confirmacao(request, sessao_id)


def _run_atendimento_pesquisa(request: ChatAtendimentoRequest, sessao_id: uuid.UUID) -> ChatAtendimentoResponse:
    agente = build_agente_atendente(build_llm(temperature=0.3))
    task = Task(
        description=(
            f'O cliente disse: "{request.mensagem}". A filial de atendimento é {request.filial_id}. '
            "Siga rigorosamente seu fluxo de atendimento: busque o produto ou princípio ativo adequado, "
            "verifique o estoque nessa filial e, se necessário, busque substitutos genéricos. Nunca "
            "invente produto_id — use somente os que vieram das ferramentas de busca."
        ),
        expected_output=(
            "Uma resposta simpática ao cliente e a lista de produtos realmente sugeridos, com "
            "produto_id, nome, disponibilidade, preço e o motivo da sugestão."
        ),
        agent=agente,
        output_pydantic=RespostaAtendimentoOutput,
    )
    crew = Crew(agents=[agente], tasks=[task], process=Process.sequential, verbose=True)
    resultado = crew.kickoff()
    saida: RespostaAtendimentoOutput = resultado.pydantic  # type: ignore[assignment]

    tipo_decisao = TipoDecisaoEnum.sugestao_similar if saida.produtos_sugeridos else TipoDecisaoEnum.alerta_estoque
    principio_ativo_id = uuid.UUID(saida.principio_ativo_id) if saida.principio_ativo_id else None
    log_id = registrar_auditoria(
        role=AgentRole.ATENDENTE,
        tipo_decisao=tipo_decisao,
        entidade_afetada="produtos",
        decisao_tomada=saida.resposta_texto,
        dados_base=saida.model_dump(),
        principio_ativo_id=principio_ativo_id,
        sessao_id=sessao_id,
    )

    return ChatAtendimentoResponse(
        sessao_id=sessao_id,
        resposta=saida.resposta_texto,
        produtos_sugeridos=[
            ProdutoSugeridoResponse(
                produto_id=uuid.UUID(p.produto_id),
                nome_comercial=p.nome_comercial,
                disponivel=p.disponivel,
                preco=p.preco,
                motivo_sugestao=p.motivo_sugestao,
            )
            for p in saida.produtos_sugeridos
        ],
        venda_id=None,
        log_auditoria_id=log_id,
    )


def _run_atendimento_confirmacao(request: ChatAtendimentoRequest, sessao_id: uuid.UUID) -> ChatAtendimentoResponse:
    if request.produto_id is None:
        raise ValueError("produto_id é obrigatório quando confirmar_compra=true")

    produto = _buscar_produto_basico(request.produto_id)
    if produto is None:
        raise ValueError("produto_id não encontrado (ou não é um MIP visível para o atendente)")

    lote_id = request.lote_id or _buscar_lote_disponivel(request.produto_id, request.filial_id)
    if lote_id is None:
        raise ValueError("Nenhum lote com estoque disponível para este produto nesta filial")

    valor_total = float(produto["preco_tabela"]) * request.quantidade

    agente = build_agente_atendente(build_llm(temperature=0.1))
    task = Task(
        description=(
            f"O cliente confirmou a compra do produto '{produto['nome_comercial']}', "
            f"quantidade {request.quantidade}, valor total R${valor_total:.2f}. Processe o pagamento com "
            "processar_pagamento_mock e, somente se aprovado, gere a nota fiscal com "
            "gerar_nota_fiscal_mock. Responda de forma simpática confirmando (ou não) a compra."
        ),
        expected_output="Confirmação estruturada com sucesso, transacao_id, nfe_chave e uma resposta simpática.",
        agent=agente,
        output_pydantic=ConfirmacaoCompraOutput,
    )
    crew = Crew(agents=[agente], tasks=[task], process=Process.sequential, verbose=True)
    resultado = crew.kickoff()
    saida: ConfirmacaoCompraOutput = resultado.pydantic  # type: ignore[assignment]

    venda_id: uuid.UUID | None = None
    if saida.sucesso:
        with agent_session(AgentRole.ATENDENTE) as session:
            venda = Venda(
                filial_id=request.filial_id,
                cliente_id=request.cliente_id,
                agente_atendimento_id=agente_id_for(AgentRole.ATENDENTE),
                canal=CanalVendaEnum.avatar_ia,
                valor_total=Decimal(str(valor_total)),
                forma_pagamento="cartao",
            )
            session.add(venda)
            session.flush()
            session.add(
                VendaItem(
                    venda_id=venda.id,
                    produto_id=request.produto_id,
                    lote_id=lote_id,
                    quantidade=request.quantidade,
                    preco_unitario=produto["preco_tabela"],
                )
            )
            session.flush()
            venda_id = venda.id

    log_id = registrar_auditoria(
        role=AgentRole.ATENDENTE,
        tipo_decisao=TipoDecisaoEnum.aprovacao_compra,
        entidade_afetada="vendas",
        entidade_id=venda_id,
        decisao_tomada=saida.resposta_texto,
        dados_base={
            **saida.model_dump(),
            "produto_id": str(request.produto_id),
            "quantidade": request.quantidade,
            "valor_total": valor_total,
        },
        sessao_id=sessao_id,
    )

    return ChatAtendimentoResponse(
        sessao_id=sessao_id,
        resposta=saida.resposta_texto,
        produtos_sugeridos=[],
        venda_id=venda_id,
        log_auditoria_id=log_id,
    )
