-- FASE 4 (LLM-06): histórico real de conversa por sessao_id. Antes disso
-- cada mensagem do chat era tratada de forma isolada — o atendente "esquecia"
-- tudo entre uma chamada e outra do mesmo cliente na mesma sessão. Postgres é
-- suficiente para o piloto (baixo volume, já é a fonte de verdade de tudo
-- mais); Redis fica documentado como otimização futura se o volume justificar
-- (ver comentário em app/agents/service.py).
--
-- Append-only de propósito, igual logs_auditoria: nenhuma role recebe
-- UPDATE/DELETE (nem aqui, nem em 0011/0012) — não existe caso de negócio
-- para editar ou apagar uma mensagem já trocada.
CREATE TABLE IF NOT EXISTS sessoes_chat_mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id UUID NOT NULL,
    papel VARCHAR(10) NOT NULL CHECK (papel IN ('cliente', 'avatar')),
    mensagem TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessoes_chat_mensagens_sessao ON sessoes_chat_mensagens (sessao_id, criado_em);

ALTER TABLE sessoes_chat_mensagens ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT ON sessoes_chat_mensagens TO agente_atendente;
GRANT SELECT ON sessoes_chat_mensagens TO app_backend;

CREATE POLICY ins_atendente ON sessoes_chat_mensagens FOR INSERT
    TO agente_atendente WITH CHECK (true);
CREATE POLICY sel_atendente ON sessoes_chat_mensagens FOR SELECT
    TO agente_atendente USING (true);
CREATE POLICY sel_backend ON sessoes_chat_mensagens FOR SELECT
    TO app_backend USING (true);
