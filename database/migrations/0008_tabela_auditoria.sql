-- FASE 1: Auditoria total. Tabela somente-inserção — nenhuma role (nem o
-- backend da aplicação) recebe UPDATE/DELETE sobre ela (ver 0010 e 0011).
-- Registra, por decisão: o que foi decidido, com base em quais dados,
-- qual princípio ativo envolvido (quando aplicável) e quando ocorreu.

CREATE TABLE IF NOT EXISTS logs_auditoria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agente_id UUID NOT NULL REFERENCES agentes_ia(id),
    tipo_decisao tipo_decisao_enum NOT NULL,
    entidade_afetada VARCHAR(60) NOT NULL,
    entidade_id UUID,
    principio_ativo_id UUID REFERENCES principios_ativos(id),
    decisao_tomada TEXT NOT NULL,
    dados_base JSONB NOT NULL,
    justificativa TEXT,
    confianca NUMERIC(3,2) CHECK (confianca BETWEEN 0 AND 1),
    sessao_id UUID,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_auditoria_agente ON logs_auditoria (agente_id);
CREATE INDEX IF NOT EXISTS idx_logs_auditoria_principio_ativo ON logs_auditoria (principio_ativo_id);
CREATE INDEX IF NOT EXISTS idx_logs_auditoria_sessao ON logs_auditoria (sessao_id);
