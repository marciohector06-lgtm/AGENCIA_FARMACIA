# LGPD — base legal, retenção e arquitetura de privacidade

FASE 5 (última fase técnica). Este documento cobre LGPD-01 a LGPD-04:
base legal por categoria de dado, retenção, fluxo de atendimento a pedido de
titular, e a decisão arquitetural que resolve o conflito entre auditabilidade
(o produto) e o direito de eliminação (art. 18).

## 1. Base legal por categoria de dado

| Categoria | Base legal (LGPD) | Onde vive |
|---|---|---|
| Dado clínico (sintoma relatado, medicamentos em uso, sugestão de MIP, texto da conversa com o Avatar) | **Art. 11, II, "f"** — tutela da saúde, procedimento realizado por profissionais de saúde/farmacêuticos ou por entidade sanitária (o Agente Atendente atua como avatar de farmacêutico clínico) | `logs_auditoria` (decisões clínicas), `sessoes_chat_mensagens` (transcrição) — sempre via `pseudonimo_id`, nunca `cliente_id` direto |
| Dado de venda/fiscal (produto comprado, quantidade, valor, forma de pagamento, nota fiscal) | **Art. 7º, V** — execução de contrato do qual o titular é parte (a compra em si) | `vendas`, `vendas_itens`, `logs_auditoria` com `entidade_afetada='vendas'` (`cliente_id` em claro, via FK) |
| Cadastro do cliente (nome, CPF, contato) | **Art. 7º, V** (execução de contrato) e **Art. 7º, II** (obrigação legal/regulatória — emissão de nota fiscal exige CPF do consumidor) | `clientes` — acesso restrito a `app_backend`; nenhuma role de agente lê esta tabela (corrigido em LGPD-02, ver §4) |
| Consentimento para atendimento por IA | **Art. 7º, I** — consentimento do titular, especificamente para o uso de IA no atendimento clínico (além, não em substituição, à base do art. 11 para o dado de saúde em si) | `clientes.consentimento_dado` / `consentimento_lgpd_em` |

## 2. Retenção por categoria

| Categoria | Prazo | Justificativa |
|---|---|---|
| `logs_auditoria` (todas as decisões, incl. as com `pseudonimo_id`) | **5 anos** a partir de `criado_em` | Padrão de mercado para dado de saúde + fiscal no Brasil (referências: prazo decadencial fiscal de 5 anos — CTN art. 173/174 — e prontuário/registro de atendimento em saúde). Após 5 anos, elegível para expurgo/arquivamento frio; a linha nunca é alterada antes disso (append-only) |
| `sessoes_chat_mensagens` | Mesma janela de 5 anos, acompanhando `logs_auditoria` (mesma sessão, mesma justificativa) | Idem |
| `vendas` / `vendas_itens` | **5 anos** (prazo fiscal) | Obrigação legal de guarda de documento fiscal |
| `pseudonimos_titular` | Sem prazo de expurgo automático — mas **revogável a qualquer momento** a pedido do titular (LGPD-04) | Não é um log de evento, é uma tabela de mapeamento viva; revogar é o mecanismo de eliminação, não um cron de idade |
| `clientes` (cadastro) | Enquanto a relação comercial existir; elimina-se via `DELETE /clientes/{id}` a pedido do titular (fora do prazo fiscal de `vendas`, que sobrevive por FK `ON DELETE SET NULL`) | — |

Expurgo automático por idade (job agendado) não está implementado nesta fase — é um TODO de operação, não de arquitetura: a retenção de 5 anos está documentada e as tabelas são append-only, prontas para um `pg_cron` de expurgo quando o volume justificar (mesma decisão já tomada para `fn_atualizar_lotes_vencidos`, migration 0013).

## 3. Fluxo de atendimento a pedido de titular

### Eliminação (art. 18, VI) — dado clínico
`DELETE /clientes/{id}/dados-clinicos` → revoga o pseudônimo ativo do titular
(`pseudonimos_titular.revogado_em = now()`, `cliente_id = NULL`). As linhas de
`logs_auditoria`/`sessoes_chat_mensagens` que apontam pro `pseudonimo_id`
continuam existindo — a prova da decisão da IA é preservada, só deixa de ser
resolvível a uma pessoa. Uma nova sessão de atendimento do mesmo cliente, no
futuro, gera um pseudônimo novo (não reabre o antigo).

### Eliminação (art. 18, VI) — cadastro completo
`DELETE /clientes/{id}` remove o cadastro. `vendas.cliente_id` e
`pseudonimos_titular.cliente_id` viram `NULL` (`ON DELETE SET NULL`) — o
histórico fiscal de vendas sobrevive (base legal própria, art. 7º V/II, fora
do escopo do pedido de eliminação de dado clínico), só perde a referência ao
titular removido.

### Acesso (art. 18, II) e portabilidade (art. 18, V)
`GET /clientes/{id}` devolve o cadastro. Dado clínico do titular (mensagens,
decisões da IA que o envolveram) é localizável via `pseudonimo_id` —
hoje não há um endpoint dedicado de exportação; é um TODO de produto, não
bloqueia a arquitetura (a rastreabilidade pseudonimo_id → sessão está pronta
para alimentar um relatório assim que houver demanda real).

### Consentimento (art. 8º) — atendimento por IA
Primeira interação de um cliente identificado: `POST /clientes/{id}/consentimento`
grava `consentimento_dado=true` e `consentimento_lgpd_em=now()`. Sem isso,
`POST /chat/atendimento` com `cliente_id` preenchido devolve **403**. Atendimento
anônimo (sem `cliente_id`) nunca passa por essa checagem — não há titular
identificado para consentir.

## 4. Decisão arquitetural: pseudonimização

**O conflito:** `logs_auditoria` é append-only por design — é a prova de que
cada decisão da IA (sugestão de produto, bloqueio de venda, aprovação de
desconto) foi tomada com base em dados reais, nunca alucinada. É o fosso
competitivo do produto. A LGPD art. 18 garante ao titular o direito de
eliminação. Os dois são incompatíveis se o dado clínico estiver ligado ao CPF
na própria linha de auditoria.

**A solução:** o dado clínico entra na auditoria desvinculado do titular. A
ligação vive só em `pseudonimos_titular` (`pseudonimo_id` UUID ↔ `cliente_id`),
acessível exclusivamente por `app_backend` — nenhuma role de agente de IA
enxerga essa tabela (nem leitura), testado como as demais políticas de
permissão do sistema.

- `logs_auditoria.pseudonimo_id` e `sessoes_chat_mensagens.pseudonimo_id`
  (nunca `cliente_id`) são a única referência a um titular em dado clínico.
- Revogar = `UPDATE pseudonimos_titular SET revogado_em = now(), cliente_id = NULL`.
  Nunca um `DELETE` — a linha de auditoria referenciada por `pseudonimo_id`
  continua existindo e válida (FK aponta pra `pseudonimos_titular`, não pra
  `clientes`), só perde a capacidade de ser resolvida a uma pessoa.
- **Por que isso preserva a auditabilidade:** a pergunta que `logs_auditoria`
  precisa responder é "por que a IA decidiu X" — produto_id, princípio ativo,
  raciocínio, modelo/tokens/latência. Nunca precisou responder "quem era o
  cliente" para isso. Separar as duas perguntas em tabelas diferentes, com
  controle de acesso diferente, é o que permite atender as duas exigências
  (auditoria íntegra + direito de eliminação) sem que uma sacrifique a outra.
- **O que continua em claro, de propósito:** `vendas.cliente_id` — a nota
  fiscal precisa do titular real, com base legal própria (art. 7º V/II,
  obrigação fiscal) que não está sujeita ao mesmo pedido de eliminação de
  dado clínico. `logs_auditoria` com `entidade_afetada='vendas'` também fica
  como está (resolvível via `entidade_id → vendas.cliente_id`) — pseudonimizar
  essas linhas seria redundante, o vínculo ali é intrínseco à transação
  fiscal, não ao histórico clínico.
- **Risco residual documentado, não "corrigido" tecnicamente:** dentro da
  *mesma sessão de atendimento*, no momento em que uma compra é confirmada, a
  correlação sessão-clínica ↔ identidade é operacionalmente inevitável (quem
  processa a venda precisa saber pra quem é a nota fiscal). Isso é aceitável:
  tem base legal própria e fica restrito às roles que já processam a
  transação (`agente_atendente`, `app_backend`). A pseudonimização resolve o
  que a LGPD realmente exige — a capacidade de eliminar o vínculo
  permanentemente a pedido do titular — não a impossibilidade teórica de
  qualquer correlação pontual durante uma transação real em andamento.

### LGPD-02 — correção de acesso a CPF

Auditoria de grants (LGPD-02) encontrou `agente_orquestrador` com `GRANT
SELECT ON ALL TABLES IN SCHEMA public` (migration 0011) + policy própria
(migration 0014) dando acesso de leitura a `clientes.cpf`, sem nenhuma
tool/caso de uso que precisasse disso. Revogado na mesma migration da
pseudonimização (`0002_lgpd_04...`, atômico de propósito — ou a
pseudonimização entra completa com isso corrigido, ou nada entra). Nenhuma
role de agente tem acesso a `clientes` a partir desta fase; nenhum
serializer/prompt/`dados_base` de auditoria inclui CPF (confirmado por grep
em toda a árvore `app/`).
