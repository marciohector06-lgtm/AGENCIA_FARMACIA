-- FASE 3/4: Registro dos 4 agentes de IA na tabela agentes_ia. É a essas linhas
-- que precificacao_historico.proposto_por_agente_id / aprovado_por_agente_id e
-- logs_auditoria.agente_id apontam — sem elas nenhum agente consegue gravar nada.
-- db_role_name liga cada linha à role Postgres correspondente (migration 0011),
-- que é a credencial de fato usada pela camada Python (app/agents/db_sync.py).

INSERT INTO agentes_ia (tipo, nome, descricao, db_role_name, modelo_llm, versao)
VALUES
    (
        'atendente',
        'Farmacêutico Clínico',
        'Atendimento ao cliente/avatar: sugestão de MIPs por princípio ativo, checagem de estoque e substitutos.',
        'agente_atendente',
        'gemini-2.5-pro',
        '1.0.0'
    ),
    (
        'gerente_estoque',
        'Analista de Varejo Sênior',
        'Giro de estoque, curva ABC e proposição de descontos para lotes próximos do vencimento.',
        'agente_estoque',
        'gemini-2.5-pro',
        '1.0.0'
    ),
    (
        'financeiro',
        'CFO',
        'Aprovação de descontos com base em margem e simulação de fluxo de caixa.',
        'agente_financeiro',
        'gemini-2.5-pro',
        '1.0.0'
    ),
    (
        'orquestrador',
        'CEO',
        'Coordenação entre agentes, resolução de conflitos e consolidação para o dashboard.',
        'agente_orquestrador',
        'gemini-2.5-pro',
        '1.0.0'
    )
ON CONFLICT (tipo, nome) DO NOTHING;
