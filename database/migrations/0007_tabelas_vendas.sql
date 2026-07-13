-- FASE 1: Clientes e vendas (inclui vendas originadas pelo Avatar/Agente Atendente).

CREATE TABLE IF NOT EXISTS clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(150) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    data_nascimento DATE,
    telefone VARCHAR(20),
    email VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vendas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filial_id UUID NOT NULL REFERENCES filiais(id) ON DELETE RESTRICT,
    cliente_id UUID REFERENCES clientes(id) ON DELETE SET NULL,
    agente_atendimento_id UUID REFERENCES agentes_ia(id) ON DELETE SET NULL,
    canal canal_venda_enum NOT NULL DEFAULT 'balcao',
    valor_total NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (valor_total >= 0),
    forma_pagamento VARCHAR(30),
    data_venda TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vendas_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venda_id UUID NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    lote_id UUID NOT NULL REFERENCES lotes(id) ON DELETE RESTRICT,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10,2) NOT NULL CHECK (preco_unitario >= 0),
    desconto_aplicado NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (desconto_aplicado BETWEEN 0 AND 100),
    subtotal NUMERIC(10,2) GENERATED ALWAYS AS (
        ROUND(quantidade * preco_unitario * (1 - desconto_aplicado / 100.0), 2)
    ) STORED
);
