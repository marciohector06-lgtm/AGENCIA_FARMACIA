-- FASE 1: Tabelas de apoio (lojas, fabricantes e registro dos agentes de IA).

CREATE TABLE IF NOT EXISTS filiais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(120) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    endereco VARCHAR(255),
    cidade VARCHAR(100),
    uf CHAR(2),
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fabricantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(150) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    registro_anvisa VARCHAR(30),
    pais_origem VARCHAR(60) NOT NULL DEFAULT 'Brasil',
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Registro dos agentes de IA. db_role_name liga cada agente à role Postgres
-- criada em 0010_roles_grants.sql, permitindo rastrear no log de auditoria
-- exatamente qual credencial tomou cada decisão.
CREATE TABLE IF NOT EXISTS agentes_ia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo tipo_agente_enum NOT NULL,
    nome VARCHAR(80) NOT NULL,
    descricao TEXT,
    db_role_name VARCHAR(63) NOT NULL,
    modelo_llm VARCHAR(80) NOT NULL DEFAULT 'gemini-1.5-pro',
    versao VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tipo, nome)
);
