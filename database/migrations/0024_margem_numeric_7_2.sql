-- FASE 3 (BUG-05): margem_resultante NUMERIC(5,2) só comporta -999,99 a
-- 999,99. Um preço de liquidação bem abaixo do custo (ex.: R$2 de preço novo
-- contra R$30 de custo) já produz margem = -1400%, estourando o CHECK
-- implícito da precisão da coluna com "numeric field overflow" — exatamente
-- no cenário que o CFO (backstory do Agente Financeiro) é instruído a aceitar
-- ("liquidar lote perto do vencimento"). NUMERIC(7,2) comporta até
-- ±99999,99; o clamp defensivo em financeiro_tools.py (±9999,99) é mais
-- conservador ainda, então nunca deveria colidir com o teto da coluna — a
-- largura maior aqui é rede de segurança adicional, não a única defesa.
ALTER TABLE precificacao_historico ALTER COLUMN margem_resultante TYPE NUMERIC(7, 2);
