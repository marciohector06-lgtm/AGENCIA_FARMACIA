-- FASE 2 (CLIN-01 + CLIN-02): "First-Expired-First-Out" virou "primeiro que
-- vence, mesmo que já tenha vencido" porque dias_para_vencer fica negativo
-- num lote vencido e ainda assim ordenava primeiro — e a view nunca filtrou
-- por status.
--
-- ATENÇÃO (achado testando contra Postgres real, não hipótese): ao contrário
-- do que o comentário original desta migration assumia, CREATE OR REPLACE
-- VIEW NÃO preserva security_invoker=on setado por um ALTER VIEW anterior —
-- reseta pra off. Sem o ALTER VIEW abaixo repetido, o SEC-03 regredia
-- silenciosamente. O teste de RLS-via-view da FASE 1 pegou isso.
CREATE OR REPLACE VIEW vw_estoque_atual AS
SELECT
    e.id AS estoque_id,
    f.id AS filial_id,
    f.nome AS filial_nome,
    p.id AS produto_id,
    p.nome_comercial,
    p.tarja,
    l.id AS lote_id,
    l.numero_lote,
    l.data_validade,
    (l.data_validade - CURRENT_DATE) AS dias_para_vencer,
    e.quantidade_atual,
    e.quantidade_reservada,
    (e.quantidade_atual - e.quantidade_reservada) AS quantidade_disponivel,
    l.status
FROM estoque e
JOIN lotes l ON l.id = e.lote_id
JOIN produtos p ON p.id = l.produto_id
JOIN filiais f ON f.id = e.filial_id
WHERE l.status = 'disponivel'
  AND l.data_validade >= CURRENT_DATE;

ALTER VIEW vw_estoque_atual SET (security_invoker = on);
