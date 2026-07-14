-- FASE 3 (BUG-07): rodar /agentes/analise-estoque 2x criava N linhas
-- 'proposto' pro mesmo lote — nada impedia. Índice único parcial: só um
-- 'proposto' por lote_id por vez (depois de aprovado/rejeitado, o lote pode
-- receber uma proposta nova). IF NOT EXISTS torna a migration idempotente.
CREATE UNIQUE INDEX IF NOT EXISTS idx_precificacao_lote_proposto_unico
    ON precificacao_historico (lote_id)
    WHERE status_aprovacao = 'proposto';
