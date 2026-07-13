-- FASE 1: Base clínica relacional. Tudo aqui é o que o Agente Atendente pode
-- efetivamente consultar para justificar uma sugestão — nunca texto livre solto,
-- sempre linhas de tabela com chave estrangeira para principio_ativo_id
-- (suporta a regra "Zero Alucinação Clínica" e a auditoria por princípio ativo).

CREATE TABLE IF NOT EXISTS principios_ativos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(150) NOT NULL UNIQUE,
    nome_dcb VARCHAR(150),
    classe_terapeutica VARCHAR(120) NOT NULL,
    mecanismo_acao TEXT,
    contraindicacoes_gerais TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interacoes_medicamentosas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principio_ativo_a_id UUID NOT NULL REFERENCES principios_ativos(id) ON DELETE CASCADE,
    principio_ativo_b_id UUID NOT NULL REFERENCES principios_ativos(id) ON DELETE CASCADE,
    gravidade gravidade_interacao_enum NOT NULL,
    descricao TEXT NOT NULL,
    fonte VARCHAR(150) NOT NULL DEFAULT 'Bulario ANVISA',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Ordem canônica (a_id < b_id) evita pares duplicados invertidos (A,B) vs (B,A).
    -- A aplicação deve ordenar os dois IDs antes de inserir.
    CONSTRAINT chk_ordem_canonica CHECK (principio_ativo_a_id < principio_ativo_b_id),
    CONSTRAINT uq_par_interacao UNIQUE (principio_ativo_a_id, principio_ativo_b_id)
);

CREATE TABLE IF NOT EXISTS restricoes_uso_principio_ativo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principio_ativo_id UUID NOT NULL REFERENCES principios_ativos(id) ON DELETE CASCADE,
    tipo_restricao tipo_restricao_enum NOT NULL,
    nivel nivel_restricao_enum NOT NULL,
    descricao TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (principio_ativo_id, tipo_restricao)
);
