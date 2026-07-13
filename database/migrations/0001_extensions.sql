-- FASE 1: Extensões necessárias no Postgres/Supabase.
-- pgcrypto  -> gen_random_uuid() para PKs
-- vector    -> embeddings de bulas (RAG do Agente Atendente, usado a partir da FASE 4)
-- pg_cron   -> jobs agendados (ex.: marcar lotes vencidos diariamente)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_cron;
