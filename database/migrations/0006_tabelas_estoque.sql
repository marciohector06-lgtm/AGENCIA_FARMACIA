-- FASE 1: Lotes, posição de estoque por filial e histórico de precificação
-- (fluxo Gerente de Estoque propõe -> Financeiro aprova, mediado pelo Orquestrador).

CREATE TABLE IF NOT EXISTS lotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    numero_lote VARCHAR(40) NOT NULL,
    data_fabricacao DATE NOT NULL,
    data_validade DATE NOT NULL,
    quantidade_recebida INTEGER NOT NULL CHECK (quantidade_recebida > 0),
    custo_unitario NUMERIC(10,2) NOT NULL CHECK (custo_unitario >= 0),
    status status_lote_enum NOT NULL DEFAULT 'disponivel',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_validade_apos_fabricacao CHECK (data_validade > data_fabricacao),
    UNIQUE (produto_id, numero_lote)
);

CREATE TABLE IF NOT EXISTS estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filial_id UUID NOT NULL REFERENCES filiais(id) ON DELETE RESTRICT,
    lote_id UUID NOT NULL REFERENCES lotes(id) ON DELETE RESTRICT,
    quantidade_atual INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_atual >= 0),
    quantidade_reservada INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_reservada >= 0),
    localizacao_gondola VARCHAR(30),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (filial_id, lote_id),
    CONSTRAINT chk_reserva_nao_excede_estoque CHECK (quantidade_reservada <= quantidade_atual)
);

CREATE TABLE IF NOT EXISTS precificacao_historico (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    lote_id UUID REFERENCES lotes(id) ON DELETE SET NULL,
    preco_anterior NUMERIC(10,2) NOT NULL CHECK (preco_anterior >= 0),
    preco_novo NUMERIC(10,2) NOT NULL CHECK (preco_novo >= 0),
    percentual_desconto NUMERIC(5,2) GENERATED ALWAYS AS (
        CASE WHEN preco_anterior = 0 THEN 0
        ELSE ROUND(((preco_anterior - preco_novo) / preco_anterior) * 100, 2) END
    ) STORED,
    margem_resultante NUMERIC(5,2),
    motivo TEXT NOT NULL,
    proposto_por_agente_id UUID NOT NULL REFERENCES agentes_ia(id),
    aprovado_por_agente_id UUID REFERENCES agentes_ia(id),
    status_aprovacao status_aprovacao_enum NOT NULL DEFAULT 'proposto',
    aprovado_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
