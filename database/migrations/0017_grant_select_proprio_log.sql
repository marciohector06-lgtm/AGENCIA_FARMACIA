-- FASE 3/4 (correção): INSERT ... RETURNING (usado pelo SQLAlchemy para ler de
-- volta o criado_em gerado pelo servidor) exige privilégio de SELECT no Postgres,
-- não só INSERT. A migration 0011 só deu SELECT em logs_auditoria para
-- agente_orquestrador e app_backend — os outros 3 agentes conseguiam INSERT mas
-- não conseguiam ler de volta a própria linha, e o INSERT falhava inteiro.
--
-- Correção: cada agente pode enxergar (SELECT) só as PRÓPRIAS linhas de
-- auditoria — nunca as dos outros agentes. O GRANT é de tabela inteira, mas o
-- RLS abaixo restringe de fato as linhas visíveis.

CREATE OR REPLACE FUNCTION current_agente_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT id FROM agentes_ia WHERE db_role_name = current_user LIMIT 1;
$$;

GRANT SELECT ON logs_auditoria TO agente_atendente, agente_estoque, agente_financeiro;

CREATE POLICY sel_proprio_agente ON logs_auditoria FOR SELECT
    TO agente_atendente, agente_estoque, agente_financeiro
    USING (agente_id = current_agente_id());
