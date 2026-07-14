-- FASE 1 (SEC-10): rotação das senhas placeholder de 0011_roles_grants.sql.
-- 0011 é append-only (nunca editar) e criou 5 roles com senha
-- CHANGE_ME_<ROLE> só pra a migration rodar — se isso for aplicado num
-- Postgres real sem trocar as senhas, são credenciais públicas (estão neste
-- repositório). Procedimento de rotação, uma vez por role
-- (agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador,
-- app_backend):
--   1. Gere uma senha forte: python -c "import secrets; print(secrets.token_urlsafe(24))"
--   2. ALTER ROLE <role> WITH PASSWORD '<senha gerada>';
--   3. Atualize a connection string correspondente no .env (DATABASE_URL* —
--      ver backend/.env.example) com a MESMA senha, url-encoded se tiver
--      caractere especial (@ -> %40).
-- Nunca reaproveite os placeholders CHANGE_ME_* fora de um ambiente
-- descartável de desenvolvimento local.

-- FASE 1 (SEC-01): autenticação mínima. Não é um sistema de usuários — é só
-- o suficiente pra distinguir "token válido" de "token inválido" (permissões
-- finas por operador vêm depois). python-jose valida o JWT na aplicação;
-- esta tabela só guarda quem pode logar e a senha con hash bcrypt (passlib).

CREATE TABLE IF NOT EXISTS operadores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(150) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: só app_backend toca esta tabela (o login roda como app_backend, igual
-- qualquer outro endpoint administrativo) — nenhum agente de IA precisa
-- (nem deve) enxergar credenciais de operador.
ALTER TABLE operadores ENABLE ROW LEVEL SECURITY;
CREATE POLICY all_backend ON operadores FOR ALL TO app_backend USING (true) WITH CHECK (true);
GRANT SELECT, INSERT, UPDATE ON operadores TO app_backend;

-- Bootstrap: um operador inicial, mesmo padrão de placeholder já usado em
-- 0011 para as senhas de role — TROQUE antes de expor isto fora de um
-- ambiente controlado. Rotação (sem editar esta migration, que é
-- append-only): gere um novo hash bcrypt e rode um UPDATE direto, ex.:
--   python -c "from passlib.context import CryptContext; \
--     print(CryptContext(schemes=['bcrypt']).hash('sua-senha-nova'))"
--   UPDATE operadores SET senha_hash = '<hash gerado>' WHERE email = 'operador@farmacia.local';
-- O mesmo procedimento vale para girar as senhas das roles de banco criadas
-- em 0011 (ALTER ROLE <role> WITH PASSWORD '...' com uma senha forte gerada
-- via secrets.token_urlsafe, nunca reaproveitando os placeholders CHANGE_ME_*).
INSERT INTO operadores (email, senha_hash)
VALUES ('operador@farmacia.local', '$2b$12$EuL8H31QloyIZx6L/i5wceox4mg13ugdjWHj7LgRV34.OD6IDvuWK')
ON CONFLICT (email) DO NOTHING;
