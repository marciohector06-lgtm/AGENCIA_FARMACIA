-- FASE 1: Row Level Security. Isto é defesa em profundidade sobre os GRANTs de
-- 0011: mesmo que uma role ganhe um privilégio de coluna/tabela por engano no
-- futuro, a política de linha ainda barra o acesso indevido.

-- ---------------------------------------------------------------------------
-- principios_ativos / interacoes_medicamentosas / restricoes_uso_principio_ativo / bulas
-- Dados clínicos: leitura ampla para os agentes que precisam deles, escrita só
-- pelo backend (cadastro/curadoria de conteúdo clínico não é feito por agente).
-- ---------------------------------------------------------------------------
ALTER TABLE principios_ativos ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_agentes ON principios_ativos FOR SELECT
    TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador USING (true);
CREATE POLICY all_backend ON principios_ativos FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE interacoes_medicamentosas ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_agentes ON interacoes_medicamentosas FOR SELECT
    TO agente_atendente, agente_orquestrador USING (true);
CREATE POLICY all_backend ON interacoes_medicamentosas FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE restricoes_uso_principio_ativo ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_agentes ON restricoes_uso_principio_ativo FOR SELECT
    TO agente_atendente, agente_orquestrador USING (true);
CREATE POLICY all_backend ON restricoes_uso_principio_ativo FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE bulas ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_agentes ON bulas FOR SELECT
    TO agente_atendente, agente_orquestrador USING (true);
CREATE POLICY all_backend ON bulas FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- produtos: a regra clínica central. O Agente Atendente só enxerga produtos
-- isentos de prescrição (tarja = 'isento') e ativos — nunca tarja vermelha/preta.
-- ---------------------------------------------------------------------------
ALTER TABLE produtos ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_atendente_mip ON produtos FOR SELECT
    TO agente_atendente USING (tarja = 'isento' AND ativo = true);
CREATE POLICY sel_estoque_all ON produtos FOR SELECT TO agente_estoque USING (true);
CREATE POLICY sel_financeiro_all ON produtos FOR SELECT TO agente_financeiro USING (true);
CREATE POLICY sel_orquestrador_all ON produtos FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY upd_financeiro_precos ON produtos FOR UPDATE TO agente_financeiro USING (true) WITH CHECK (true);
CREATE POLICY all_backend ON produtos FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- lotes
-- ---------------------------------------------------------------------------
ALTER TABLE lotes ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_atendente ON lotes FOR SELECT TO agente_atendente USING (true);
CREATE POLICY sel_financeiro ON lotes FOR SELECT TO agente_financeiro USING (true);
CREATE POLICY sel_orquestrador ON lotes FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_gerente ON lotes FOR ALL TO agente_estoque USING (true) WITH CHECK (true);
CREATE POLICY all_backend ON lotes FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- estoque
-- ---------------------------------------------------------------------------
ALTER TABLE estoque ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_atendente ON estoque FOR SELECT TO agente_atendente USING (true);
CREATE POLICY sel_financeiro ON estoque FOR SELECT TO agente_financeiro USING (true);
CREATE POLICY sel_orquestrador ON estoque FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_gerente ON estoque FOR ALL TO agente_estoque USING (true) WITH CHECK (true);
CREATE POLICY all_backend ON estoque FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- precificacao_historico: o Gerente só consegue inserir propostas (nunca já
-- aprovadas); só o Financeiro pode transicionar o status de aprovação.
-- ---------------------------------------------------------------------------
ALTER TABLE precificacao_historico ENABLE ROW LEVEL SECURITY;
CREATE POLICY ins_gerente_propoe ON precificacao_historico FOR INSERT
    TO agente_estoque WITH CHECK (status_aprovacao = 'proposto');
CREATE POLICY sel_gerente ON precificacao_historico FOR SELECT TO agente_estoque USING (true);
CREATE POLICY sel_financeiro ON precificacao_historico FOR SELECT TO agente_financeiro USING (true);
CREATE POLICY upd_financeiro_aprova ON precificacao_historico FOR UPDATE
    TO agente_financeiro USING (true) WITH CHECK (true);
CREATE POLICY sel_orquestrador ON precificacao_historico FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_backend ON precificacao_historico FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- vendas / vendas_itens: o Atendente só insere vendas do canal avatar_ia.
-- ---------------------------------------------------------------------------
ALTER TABLE vendas ENABLE ROW LEVEL SECURITY;
CREATE POLICY ins_atendente ON vendas FOR INSERT
    TO agente_atendente WITH CHECK (canal = 'avatar_ia');
CREATE POLICY sel_todos_agentes ON vendas FOR SELECT
    TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador USING (true);
CREATE POLICY all_backend ON vendas FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE vendas_itens ENABLE ROW LEVEL SECURITY;
CREATE POLICY ins_atendente ON vendas_itens FOR INSERT
    TO agente_atendente WITH CHECK (
        EXISTS (SELECT 1 FROM vendas v WHERE v.id = venda_id AND v.canal = 'avatar_ia')
    );
CREATE POLICY sel_todos_agentes ON vendas_itens FOR SELECT
    TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador USING (true);
CREATE POLICY all_backend ON vendas_itens FOR ALL TO app_backend USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- logs_auditoria: todos os agentes podem inserir seus próprios registros;
-- nenhuma role tem policy de UPDATE/DELETE — combinado com a ausência do
-- GRANT correspondente em 0011, a auditoria é imutável em qualquer camada.
-- ---------------------------------------------------------------------------
ALTER TABLE logs_auditoria ENABLE ROW LEVEL SECURITY;
CREATE POLICY ins_todos_agentes ON logs_auditoria FOR INSERT
    TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador WITH CHECK (true);
CREATE POLICY sel_orquestrador ON logs_auditoria FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY sel_backend ON logs_auditoria FOR SELECT TO app_backend USING (true);
