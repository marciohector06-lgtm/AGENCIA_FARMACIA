-- FASE 1: Tipos enumerados. Uso DO blocks para permitir re-execução idempotente
-- (CREATE TYPE não aceita IF NOT EXISTS nativamente).

DO $$ BEGIN
    CREATE TYPE tarja_enum AS ENUM ('isento', 'amarela', 'vermelha', 'preta');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE forma_farmaceutica_enum AS ENUM (
        'comprimido', 'capsula', 'xarope', 'pomada', 'gel', 'creme',
        'solucao', 'suspensao', 'injetavel', 'spray', 'adesivo',
        'po', 'supositorio', 'colirio'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE via_administracao_enum AS ENUM (
        'oral', 'topica', 'injetavel', 'retal', 'oftalmica',
        'nasal', 'inalatoria', 'sublingual', 'otologica', 'vaginal'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE unidade_concentracao_enum AS ENUM ('mg', 'g', 'ml', 'mcg', 'ui', 'pct');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE status_lote_enum AS ENUM ('disponivel', 'reservado', 'vencido', 'bloqueado', 'devolvido');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE canal_venda_enum AS ENUM ('balcao', 'avatar_ia', 'app', 'delivery');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE tipo_restricao_enum AS ENUM (
        'gestante', 'lactante', 'pediatrico', 'idoso',
        'insuficiencia_renal', 'insuficiencia_hepatica', 'hipertenso', 'diabetico'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE nivel_restricao_enum AS ENUM ('contraindicado', 'cautela', 'ajuste_dose');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE gravidade_interacao_enum AS ENUM ('leve', 'moderada', 'grave', 'contraindicada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE tipo_agente_enum AS ENUM ('atendente', 'gerente_estoque', 'financeiro', 'orquestrador');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE tipo_decisao_enum AS ENUM (
        'sugestao_similar', 'ajuste_preco', 'alerta_estoque',
        'aprovacao_compra', 'bloqueio_venda', 'recomendacao_giro', 'resolucao_conflito'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE status_aprovacao_enum AS ENUM ('proposto', 'aprovado', 'rejeitado', 'auto_aprovado');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
