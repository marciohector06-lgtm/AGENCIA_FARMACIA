-- FASE 2 (CLIN-07): decisão consciente de NÃO implementar o RAG agora.
-- bulas.embedding VECTOR(1536) + o índice ivfflat existiam desde a FASE 1
-- sem nenhuma ingestão nem tool que os usasse — pior que ausência de RAG,
-- porque sugere uma capacidade que não existe. 1536 também é a dimensão do
-- text-embedding-3-small da OpenAI; o projeto usa Gemini (768/3072 conforme
-- o modelo), então mesmo se algo tivesse escrito nessa coluna a dimensão
-- estaria errada. Quando o RAG for implementado de verdade, começa do zero
-- com a dimensão certa do modelo escolhido — nunca reaproveitando isto.
DROP INDEX IF EXISTS idx_bulas_embedding;
ALTER TABLE bulas DROP COLUMN IF EXISTS embedding;
