-- FASE 0: Fronteira do ERP. A partir daqui o Postgres deixa de ser dono de
-- produtos/lotes/estoque/filiais/vendas e passa a ser um ESPELHO auditável do
-- ERP da farmácia (app/integrations/). A "origem" de cada linha decide quem
-- pode escrevê-la: uma origem de ERP (ex.: 'mock', 'linx', 'trier') é
-- somente leitura pela API — o ERP é dono. origem='manual' continua
-- totalmente editável, porque existe farmácia sem ERP nenhum, e nesse caso
-- este sistema é legitimamente a fonte da verdade (decisão registrada em
-- conversa: não fechamos esse segmento de mercado).
--
-- DEFAULT 'manual' preserva o comportamento atual para toda linha já
-- existente (cadastrada via CRUD antes desta migration): continuam editáveis
-- normalmente, ninguém perde acesso ao que já tinha.

ALTER TABLE produtos
    ADD COLUMN IF NOT EXISTS id_externo VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;

ALTER TABLE lotes
    ADD COLUMN IF NOT EXISTS id_externo VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;

ALTER TABLE estoque
    ADD COLUMN IF NOT EXISTS id_externo VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;

ALTER TABLE filiais
    ADD COLUMN IF NOT EXISTS id_externo VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS id_externo VARCHAR(64),
    ADD COLUMN IF NOT EXISTS origem VARCHAR(30) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS sincronizado_em TIMESTAMPTZ;

-- UNIQUE (origem, id_externo): chave de upsert do sync worker (F0-03). Linhas
-- manuais ficam com id_externo NULL, e o Postgres nunca considera dois NULLs
-- conflitantes numa UNIQUE constraint — não precisa de índice parcial.
DO $$ BEGIN
    ALTER TABLE produtos ADD CONSTRAINT uq_produtos_origem_id_externo UNIQUE (origem, id_externo);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE lotes ADD CONSTRAINT uq_lotes_origem_id_externo UNIQUE (origem, id_externo);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE estoque ADD CONSTRAINT uq_estoque_origem_id_externo UNIQUE (origem, id_externo);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE filiais ADD CONSTRAINT uq_filiais_origem_id_externo UNIQUE (origem, id_externo);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE vendas ADD CONSTRAINT uq_vendas_origem_id_externo UNIQUE (origem, id_externo);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------------------------------------------------------------------------
-- Novo valor de decisão para o log de auditoria: alteração manual de tarja
-- (exceção inegociável — nunca via PATCH comum, sempre por endpoint
-- privilegiado e sempre auditada). ALTER TYPE ... ADD VALUE é permitido
-- dentro de migration própria (não edita 0001-0018) e é seguro em Postgres
-- 12+ (Supabase roda versão recente).
-- ---------------------------------------------------------------------------
ALTER TYPE tipo_decisao_enum ADD VALUE IF NOT EXISTS 'alteracao_tarja';

-- ---------------------------------------------------------------------------
-- movimentacoes_estoque: ledger append-only de toda mudança em
-- estoque.quantidade_atual. Fecha o SEC-11 (quantidade_atual/reservada nunca
-- são editáveis por PATCH direto — só por movimentação com motivo
-- registrado): venda, entrada manual, ajuste manual ou sincronização com o ERP.
-- ---------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE tipo_movimentacao_enum AS ENUM ('entrada', 'venda', 'ajuste', 'sincronizacao_erp');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estoque_id UUID NOT NULL REFERENCES estoque(id) ON DELETE CASCADE,
    tipo tipo_movimentacao_enum NOT NULL,
    quantidade_delta INTEGER NOT NULL CHECK (quantidade_delta <> 0),
    quantidade_resultante INTEGER NOT NULL CHECK (quantidade_resultante >= 0),
    motivo TEXT NOT NULL,
    venda_id UUID REFERENCES vendas(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_movimentacoes_estoque_estoque_id ON movimentacoes_estoque (estoque_id);

-- RLS: tabela nova no schema public do Supabase nasce com RLS habilitada e
-- zero policies (mesma armadilha documentada em 0014) — sem isto, ninguém
-- (nem app_backend) consegue gravar movimentação alguma.
ALTER TABLE movimentacoes_estoque ENABLE ROW LEVEL SECURITY;

-- Ledger é somente leitura+inserção para todo mundo, igual logs_auditoria:
-- policies deliberadamente restritas a INSERT/SELECT (não FOR ALL) — mesmo
-- que um GRANT futuro conceda UPDATE/DELETE por engano, a RLS ainda barra.
CREATE POLICY ins_backend ON movimentacoes_estoque FOR INSERT TO app_backend WITH CHECK (true);
CREATE POLICY sel_backend ON movimentacoes_estoque FOR SELECT TO app_backend USING (true);
CREATE POLICY ins_atendente ON movimentacoes_estoque FOR INSERT TO agente_atendente WITH CHECK (true);
-- Necessária para o INSERT ... RETURNING funcionar (ver comentário do GRANT
-- abaixo) — a exposição de dado real fica limitada mesmo assim, porque o
-- GRANT de SELECT do agente_atendente é só na coluna criado_em.
CREATE POLICY sel_atendente_retorno ON movimentacoes_estoque FOR SELECT TO agente_atendente USING (true);
CREATE POLICY sel_estoque ON movimentacoes_estoque FOR SELECT TO agente_estoque USING (true);
CREATE POLICY sel_orquestrador ON movimentacoes_estoque FOR SELECT TO agente_orquestrador USING (true);

-- app_backend usa esta tabela para registrar movimentações manuais (entrada/
-- ajuste, farmácias sem ERP, endpoint POST /estoque/{id}/movimentar).
-- agente_atendente só INSERE (nunca lê o histórico de outros) o lançamento
-- 'venda' que ele mesmo gera ao confirmar uma compra (F0-06).
-- Sem UPDATE/DELETE de propósito: um lançamento errado se corrige com outro
-- lançamento (estorno), nunca editando o histórico.
GRANT SELECT, INSERT ON movimentacoes_estoque TO app_backend;
GRANT INSERT ON movimentacoes_estoque TO agente_atendente;
-- Mesma classe de bug já documentada em 0017/0018: INSERT ... RETURNING
-- (o SQLAlchemy usa isso pra ler de volta criado_em, gerado pelo servidor)
-- exige SELECT no Postgres, não só INSERT — mesmo que o código nunca
-- rode um SELECT explícito. Só a coluna retornada, não a tabela toda:
-- agente_atendente não precisa (nem deve) ler o histórico de movimentação
-- de outros agentes.
GRANT SELECT (criado_em) ON movimentacoes_estoque TO agente_atendente;
GRANT SELECT ON movimentacoes_estoque TO agente_estoque, agente_orquestrador;

-- ---------------------------------------------------------------------------
-- GRANTs mínimos novos para agente_atendente, exigidos pelo fluxo F0-06
-- (checar/confirmar venda contra o ERP e debitar o espelho local). Cada um é
-- coluna-a-coluna, não tabela inteira, seguindo a regra de menor privilégio.
-- ---------------------------------------------------------------------------

-- Precisa saber se a filial de atendimento é gerenciada por um ERP (origem/
-- id_externo) para decidir se chama o ERPAdapter — nunca precisou ler
-- filiais antes porque nunca vendia de verdade (BUG-02 pré-FASE 0).
GRANT SELECT (id, origem, id_externo) ON filiais TO agente_atendente;
CREATE POLICY sel_atendente ON filiais FOR SELECT TO agente_atendente USING (true);

-- Débito de estoque na confirmação de venda (fecha o BUG-02: antes da FASE 0
-- não existia UPDATE algum em estoque.quantidade_atual no projeto inteiro).
-- Só a coluna quantidade_atual — reserva e gôndola continuam exclusivas do
-- Agente Gerente de Estoque.
GRANT UPDATE (quantidade_atual) ON estoque TO agente_atendente;
CREATE POLICY upd_atendente_venda ON estoque FOR UPDATE TO agente_atendente USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Padrão outbox (correção pós-revisão): a ordem "confirma no ERP -> escreve
-- local" tinha uma janela onde o ERP confirma, o processo morre, e a venda
-- existe lá fora sem nenhum rastro aqui — o pior lugar possível pra esse bug
-- morar num produto cuja proposta de valor é auditabilidade. A partir de
-- agora a venda nasce 'pendente' (com a idempotency_key já persistida) na
-- MESMA transação do log de auditoria, ANTES de qualquer chamada ao ERP.
-- Só então o ERP é chamado, e só então o status vira 'confirmada' ou 'falha'.
-- Um reconciliador varre pendentes órfãs e resolve consultando o ERP pela
-- idempotency_key (F0-06/F0-07).
-- ---------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE status_confirmacao_venda_enum AS ENUM ('pendente', 'confirmada', 'falha');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS status_confirmacao status_confirmacao_venda_enum NOT NULL DEFAULT 'pendente',
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100);

DO $$ BEGIN
    ALTER TABLE vendas ADD CONSTRAINT uq_vendas_idempotency_key UNIQUE (idempotency_key);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_vendas_status_confirmacao ON vendas (status_confirmacao) WHERE status_confirmacao = 'pendente';

-- agente_atendente precisa transicionar pendente -> confirmada/falha da
-- PRÓPRIA venda (mesma trilha de canal='avatar_ia' já usada no INSERT de
-- 0012). Só a coluna de status — nada mais em vendas fica editável por ele.
GRANT UPDATE (status_confirmacao) ON vendas TO agente_atendente;
CREATE POLICY upd_atendente_status ON vendas FOR UPDATE
    TO agente_atendente USING (canal = 'avatar_ia') WITH CHECK (canal = 'avatar_ia');
