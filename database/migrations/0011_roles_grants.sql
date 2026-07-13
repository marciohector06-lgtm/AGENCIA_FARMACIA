-- FASE 1: Roles de banco por agente + backend da aplicação.
-- Cada agente de IA se conecta com uma credencial própria e limitada — nunca
-- com a role de administrador do Supabase. Troque as senhas abaixo por
-- segredos reais gerados no Supabase Vault / variáveis de ambiente antes de
-- usar em produção; aqui são apenas placeholders para a migração funcionar.

DO $$ BEGIN
    CREATE ROLE agente_atendente LOGIN PASSWORD 'CHANGE_ME_ATENDENTE';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE ROLE agente_estoque LOGIN PASSWORD 'CHANGE_ME_ESTOQUE';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE ROLE agente_financeiro LOGIN PASSWORD 'CHANGE_ME_FINANCEIRO';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE ROLE agente_orquestrador LOGIN PASSWORD 'CHANGE_ME_ORQUESTRADOR';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE ROLE app_backend LOGIN PASSWORD 'CHANGE_ME_BACKEND';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT USAGE ON SCHEMA public TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador, app_backend;

-- Baseline: nenhuma role de agente começa com qualquer privilégio.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador;

-- =========================================================================
-- Agente Atendente (Farmacêutico Clínico): leitura clínica restrita a MIPs,
-- leitura de estoque para checar disponibilidade, e registro de vendas via avatar.
-- Sem UPDATE/DELETE em nenhuma tabela.
-- =========================================================================
GRANT SELECT ON produtos, principios_ativos, interacoes_medicamentosas,
    restricoes_uso_principio_ativo, bulas, lotes, estoque, agentes_ia,
    vw_estoque_atual, vw_produtos_substituiveis TO agente_atendente;
GRANT INSERT ON vendas, vendas_itens TO agente_atendente;
GRANT INSERT ON logs_auditoria TO agente_atendente;

-- =========================================================================
-- Agente Gerente de Estoque (Analista de Varejo): gestão operacional de
-- lotes/estoque e proposição (não aprovação) de descontos.
-- =========================================================================
GRANT SELECT ON produtos, fabricantes, filiais, lotes, estoque, agentes_ia,
    vw_estoque_atual, vw_giro_estoque_90d, vendas, vendas_itens TO agente_estoque;
GRANT INSERT ON lotes, estoque TO agente_estoque;
GRANT UPDATE (status) ON lotes TO agente_estoque;
GRANT UPDATE (quantidade_atual, quantidade_reservada, localizacao_gondola, updated_at) ON estoque TO agente_estoque;
GRANT INSERT, SELECT ON precificacao_historico TO agente_estoque;
GRANT INSERT ON logs_auditoria TO agente_estoque;

-- =========================================================================
-- Agente Financeiro (CFO): aprova/rejeita descontos propostos e ajusta preços,
-- sem tocar em quantidade física de estoque.
-- =========================================================================
GRANT SELECT ON produtos, lotes, estoque, precificacao_historico, vendas,
    vendas_itens, agentes_ia, vw_giro_estoque_90d TO agente_financeiro;
GRANT UPDATE (preco_tabela, custo_medio, updated_at) ON produtos TO agente_financeiro;
GRANT UPDATE (status_aprovacao, aprovado_por_agente_id, aprovado_em) ON precificacao_historico TO agente_financeiro;
GRANT INSERT ON logs_auditoria TO agente_financeiro;

-- =========================================================================
-- Orquestrador (CEO): visão consolidada de leitura total para resolver
-- conflitos e alimentar o dashboard; não escreve diretamente em dados
-- operacionais, apenas registra suas próprias decisões de auditoria.
-- =========================================================================
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agente_orquestrador;
GRANT INSERT ON logs_auditoria TO agente_orquestrador;

-- =========================================================================
-- Backend da aplicação (FastAPI): CRUD administrativo de cadastros e
-- dashboards. Mesmo essa role NÃO recebe UPDATE/DELETE em logs_auditoria —
-- a auditoria é imutável para todo mundo.
-- =========================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON filiais, fabricantes, clientes TO app_backend;
GRANT SELECT, INSERT, UPDATE ON produtos, principios_ativos, interacoes_medicamentosas,
    restricoes_uso_principio_ativo, bulas, lotes, estoque, agentes_ia TO app_backend;
GRANT SELECT, INSERT, UPDATE ON precificacao_historico TO app_backend;
GRANT SELECT, INSERT ON vendas, vendas_itens TO app_backend;
GRANT SELECT ON logs_auditoria TO app_backend;
GRANT SELECT ON vw_estoque_atual, vw_produtos_substituiveis, vw_giro_estoque_90d TO app_backend;
