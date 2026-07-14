-- FASE 4 (LLM-08 + QA-03): logs_auditoria passa a registrar o modelo REAL
-- que executou cada decisão (resolvido em app/agents/config.py na hora da
-- chamada, nunca o campo decorativo agentes_ia.modelo_llm que ninguém
-- atualizava) mais tokens e latência — sem isso não há dado real pra decidir
-- infraestrutura/custo. Nulos em decisões que não vieram de uma chamada a
-- LLM (sync fail-closed, movimentação de estoque, etc.).
ALTER TABLE logs_auditoria
    ADD COLUMN IF NOT EXISTS modelo_llm VARCHAR(80),
    ADD COLUMN IF NOT EXISTS tokens_totais INTEGER,
    ADD COLUMN IF NOT EXISTS latencia_ms INTEGER;

-- Ajusta o seed decorativo de 0015 (nunca editar 0015 diretamente — é
-- append-only) pra pelo menos não mentir sobre o modelo atual: atendente
-- migrou pra Gemini Flash (LLM-10), os demais continuam Pro. Isto NÃO é mais
-- a fonte de verdade de auditoria (é logs_auditoria.modelo_llm agora) — é
-- só higiene, pra os dois valores não ficarem gratuitamente divergentes.
UPDATE agentes_ia SET modelo_llm = 'gemini/gemini-2.5-flash' WHERE tipo = 'atendente';
UPDATE agentes_ia SET modelo_llm = 'gemini/gemini-2.5-pro' WHERE tipo IN ('gerente_estoque', 'financeiro', 'orquestrador');
