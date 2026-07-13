-- FASE 1 (correção): filiais, fabricantes, clientes e agentes_ia vieram com RLS
-- habilitada automaticamente pelo Supabase (padrão do projeto para toda tabela
-- nova em public), mas o 0012 não previu políticas para elas — resultado:
-- bloqueio total, inclusive para app_backend, apesar dos GRANTs do 0011.
-- Alinhando as políticas com os GRANTs já existentes.

ALTER TABLE filiais ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_estoque ON filiais FOR SELECT TO agente_estoque USING (true);
CREATE POLICY sel_orquestrador ON filiais FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_backend ON filiais FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE fabricantes ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_estoque ON fabricantes FOR SELECT TO agente_estoque USING (true);
CREATE POLICY sel_orquestrador ON fabricantes FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_backend ON fabricantes FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_orquestrador ON clientes FOR SELECT TO agente_orquestrador USING (true);
CREATE POLICY all_backend ON clientes FOR ALL TO app_backend USING (true) WITH CHECK (true);

ALTER TABLE agentes_ia ENABLE ROW LEVEL SECURITY;
CREATE POLICY sel_agentes ON agentes_ia FOR SELECT
    TO agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador USING (true);
CREATE POLICY ins_upd_backend ON agentes_ia FOR ALL TO app_backend USING (true) WITH CHECK (true);
