# Deploy do backend no Render

`render.yaml` (raiz do repositório) já descreve o serviço — o Render lê esse
arquivo automaticamente ao conectar o repositório (Blueprint). Este documento
cobre só o que o Blueprint não consegue fazer sozinho: preencher os valores
reais dos segredos.

## 1. Conectar o repositório

No dashboard do Render: **New > Blueprint** → selecione este repositório
(`marciohector06-lgtm/AGENCIA_FARMACIA`) → o Render detecta `render.yaml` e
propõe criar o serviço `agencia-farmacia-backend`.

## 2. Preencher as variáveis de ambiente

Todo item com `sync: false` no `render.yaml` fica com valor vazio até você
preencher manualmente no dashboard (**Environment** do serviço, depois de
criado). Nenhum desses valores existe no repositório — preencha com os
segredos reais do seu projeto Supabase:

| Variável | De onde vem | Observação |
|---|---|---|
| `DATABASE_URL` | Supabase Dashboard → Project Settings → Database → Connection Pooling (modo **Transaction**, porta 6543), role `app_backend` | Formato: `postgresql+asyncpg://app_backend.<PROJECT_REF>:<SENHA_URL_ENCODED>@<host>:6543/postgres`. Caracteres especiais da senha (`@`, `%`, etc.) precisam estar url-encoded (`@` → `%40`) |
| `DATABASE_URL_AGENTE_ATENDENTE` | Mesma origem, role `agente_atendente` (ver `database/migrations/0011_roles_grants.sql`) | Driver **psycopg2** (síncrono), nunca asyncpg |
| `DATABASE_URL_AGENTE_ESTOQUE` | Role `agente_estoque` | Idem |
| `DATABASE_URL_AGENTE_FINANCEIRO` | Role `agente_financeiro` | Idem |
| `DATABASE_URL_AGENTE_ORQUESTRADOR` | Role `agente_orquestrador` | Idem |
| `JWT_SECRET_KEY` | Gerar com `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Nunca reaproveite a mesma chave de outro ambiente |
| `GEMINI_API_KEY` | Google AI Studio / Google Cloud Console | Chave do provedor Gemini (o único usado em produção nesta fase) |
| `CORS_ORIGINS` | Domínio real do frontend em produção, formato de lista JSON | Ex.: `["https://seu-frontend.vercel.app"]` — nunca `["*"]` |

As senhas das roles de agente (`agente_atendente`, `agente_estoque`,
`agente_financeiro`, `agente_orquestrador`, `app_backend`) são as mesmas
placeholders `CHANGE_ME_*` criadas pela migration `0011_roles_grants.sql` até
serem rotacionadas — rotação documentada em
`database/migrations/0020_operadores_auth.sql` (topo do arquivo).

## 3. Variáveis já fixadas no `render.yaml` (não precisam de ação)

| Variável | Valor | Por quê |
|---|---|---|
| `ERP_PROVIDER` | `mock` | Único adapter implementado até agora (`app/integrations/mock_adapter.py`) |
| `CREW_TIMEOUT_SECONDS` | `40` | Timeout de `crew.kickoff()` (LLM-05) — ver aviso abaixo |
| `DB_SSL_REQUIRE` | `true` | Supabase exige TLS em conexão direta |
| `GEMINI_MODEL` | `gemini/gemini-flash-latest` | Ver aviso abaixo — isto sobrescreve o modelo de **todas** as roles, não só do Atendente |

> **Por que `CREW_TIMEOUT_SECONDS=40` e não mais.** `executar_crew`
> (`app/agents/execucao.py`, LLM-05) tenta a crew até 2 vezes
> (`tentativas_max`), cada tentativa com até `CREW_TIMEOUT_SECONDS` de
> timeout — pior caso é `2 × CREW_TIMEOUT_SECONDS`. O proxy do Render (plano
> free/starter) devolve **502 sem headers de CORS** se o backend não
> responder a tempo, e um 502 sem CORS é bloqueado pelo navegador antes de
> chegar no `fetch()` — o cliente nunca vê nem o fallback JSON do backend,
> só um erro genérico de rede (foi o que aconteceu em 2026-07-18 com
> `CREW_TIMEOUT_SECONDS=90`: pior caso 180s, bem acima do timeout do proxy
> do Render). Com `40`, pior caso é 80s — mantém margem sob o timeout do
> proxy mesmo com os dois modelos (`gemini-flash-latest`/`-pro-latest`)
> ocasionalmente retentando por conta própria em cima de um 429 de cota.
> Se subir esse valor de novo, confirme o timeout real do proxy no plano
> Render em uso antes.

> **Atenção — `GEMINI_MODEL` afeta mais roles do que parece.** O código
> (`app/agents/config.py`) tem dois campos separados: `gemini_model` (default
> `gemini-pro-latest`, usado por Gerente de Estoque/Financeiro/Orquestrador) e
> `gemini_model_atendente` (default `gemini-flash-latest`, só o Atendente —
> FASE 4, decisão LLM-10: o Atendente não precisa do raciocínio pesado do Pro,
> os demais precisam). A variável de ambiente `GEMINI_MODEL` só sobrescreve o
> primeiro campo. Com o valor `gemini/gemini-flash-latest` fixado no
> `render.yaml`, **as quatro roles passam a usar Flash**, não só o Atendente —
> isto reduz custo/latência mas também a qualidade de raciocínio das roles que
> a FASE 4 decidiu manter em Pro. Se isso não for intencional, remova a
> variável `GEMINI_MODEL` do `render.yaml` (cada role volta a usar seu default
> de código) ou ajuste o valor.
>
> Os defaults usam os aliases `-latest` (em vez de uma versão numerada como
> `gemini-2.5-flash`) de propósito: em 2026-07-18 a versão numerada parou de
> responder (404 `NOT_FOUND`, "no longer available to new users") pra chaves
> de projetos novos e derrubou o atendimento em produção — os aliases
> acompanham automaticamente o modelo vigente da Google naquele nível,
> evitando que isso se repita a cada aposentadoria de versão.

## 4. Migrations em produção

O banco do Supabase já tem as 28 migrations SQL históricas aplicadas
manualmente (antes do Alembic existir) — **nunca rode `alembic upgrade head`
contra ele**, isso tentaria recriar objetos já existentes. Rode uma vez,
localmente, apontando para o Supabase de produção:

```bash
DATABASE_URL="<a mesma URL de produção, com postgresql+asyncpg://>" \
JWT_SECRET_KEY=qualquer-coisa-so-para-instanciar-settings \
python -m alembic stamp head
```

A partir daí, toda migration nova (a começar pela próxima depois desta fase)
já é aplicada normalmente com `alembic upgrade head` contra produção.

## 5. Verificar o deploy

Depois do primeiro deploy bem-sucedido, `GET https://<seu-serviço>.onrender.com/health`
deve responder `200`. Se o serviço entrar em crash-loop, o motivo mais comum é
uma variável de ambiente ausente ou com nome errado — `JWT_SECRET_KEY` e
`DATABASE_URL` não têm valor padrão no código; sem eles, a aplicação nem
termina de subir (`Settings()`/`AgentSettings()` levantam erro de validação
na inicialização).
