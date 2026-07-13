-- FASE 1: Catálogo de produtos e bulas (base para o RAG do Agente Atendente, FASE 4).

CREATE TABLE IF NOT EXISTS produtos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principio_ativo_id UUID REFERENCES principios_ativos(id) ON DELETE RESTRICT,
    fabricante_id UUID NOT NULL REFERENCES fabricantes(id) ON DELETE RESTRICT,
    nome_comercial VARCHAR(150) NOT NULL,
    codigo_barras VARCHAR(14) UNIQUE,
    registro_anvisa VARCHAR(30),
    forma_farmaceutica forma_farmaceutica_enum NOT NULL,
    via_administracao via_administracao_enum NOT NULL,
    concentracao_valor NUMERIC(10,3) NOT NULL CHECK (concentracao_valor > 0),
    concentracao_unidade unidade_concentracao_enum NOT NULL,
    quantidade_embalagem INTEGER NOT NULL CHECK (quantidade_embalagem > 0),
    tarja tarja_enum NOT NULL DEFAULT 'isento',
    -- Coluna derivada: permite políticas de RLS e queries do Agente Atendente
    -- filtrarem por "exige_prescricao = false" sem reimplementar a regra em app code.
    exige_prescricao BOOLEAN GENERATED ALWAYS AS (tarja <> 'isento') STORED,
    tipo_liberacao VARCHAR(30) NOT NULL DEFAULT 'imediata',
    preco_tabela NUMERIC(10,2) NOT NULL CHECK (preco_tabela >= 0),
    custo_medio NUMERIC(10,2) CHECK (custo_medio >= 0),
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Formas farmacêuticas de medicamento sempre precisam de princípio ativo
    -- rastreável; produtos não-medicamentosos (ex.: cosméticos) podem ficar nulos.
    CONSTRAINT chk_medicamento_precisa_principio_ativo CHECK (
        forma_farmaceutica NOT IN ('comprimido', 'capsula', 'xarope', 'injetavel', 'solucao', 'suspensao')
        OR principio_ativo_id IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS bulas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    secao VARCHAR(60) NOT NULL, -- ex.: 'indicacoes', 'posologia', 'contraindicacoes', 'advertencias'
    conteudo TEXT NOT NULL,
    embedding VECTOR(1536),
    fonte_url VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (produto_id, secao)
);

-- Índice para busca vetorial (RAG). lists=100 é um valor inicial razoável para
-- poucos milhares de linhas; ajustar quando o volume real de bulas for conhecido (FASE 4).
CREATE INDEX IF NOT EXISTS idx_bulas_embedding
    ON bulas USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
