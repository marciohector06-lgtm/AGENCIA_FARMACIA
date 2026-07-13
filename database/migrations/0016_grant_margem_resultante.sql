-- FASE 3 (correção): o GRANT original da FASE 1 (0011) esqueceu a coluna
-- margem_resultante no UPDATE de precificacao_historico concedido a
-- agente_financeiro — mas calcular e registrar a margem na aprovação é
-- exatamente o trabalho do Agente Financeiro (AprovarOuRejeitarDescontoTool).
GRANT UPDATE (margem_resultante) ON precificacao_historico TO agente_financeiro;
