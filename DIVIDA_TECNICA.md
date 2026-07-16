# Dívida técnica

## CRÍTICA — BLOQUEADOR DE PILOTO

**Repositório público + senhas `CHANGE_ME_*` das roles Postgres em texto puro
nas migrations `0011` e `0020`.**

Enquanto o repo for público e essas senhas não forem rotacionadas no Supabase
de produção, qualquer pessoa que descubra o project ref do Supabase tem
bypass total de RLS e auth direto no banco.

RISCO BAIXO para teste supervisionado com dado fictício.
BLOQUEADOR ABSOLUTO antes de qualquer dado real de paciente.

Ação obrigatória antes do piloto:
1. Rotacionar as 5 senhas de role no Supabase.
2. Atualizar as connection strings no Render.
3. Considerar tornar o repositório privado.
