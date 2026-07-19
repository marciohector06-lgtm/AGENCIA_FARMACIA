# Dívida técnica

## CRÍTICA — BLOQUEADOR DE PILOTO

**Repositório público + senhas `CHANGE_ME_*` das roles Postgres em texto puro
nas migrations `0011`, `0020` e (Agente Tributário) `0005` do Alembic.**

Enquanto o repo for público e essas senhas não forem rotacionadas no Supabase
de produção, qualquer pessoa que descubra o project ref do Supabase tem
bypass total de RLS e auth direto no banco.

RISCO BAIXO para teste supervisionado com dado fictício.
BLOQUEADOR ABSOLUTO antes de qualquer dado real de paciente.

Ação obrigatória antes do piloto:
1. Rotacionar as 6 senhas de role no Supabase (`app_backend`,
   `agente_atendente`, `agente_estoque`, `agente_financeiro`,
   `agente_orquestrador` e, a partir desta fase, `agente_tributario` —
   `ALTER ROLE agente_tributario WITH PASSWORD '<nova senha forte>';`).
2. Atualizar as connection strings no Render (inclui
   `DATABASE_URL_AGENTE_TRIBUTARIO`).
3. Considerar tornar o repositório privado.
