-- FASE 3 (BUG-01): app/agents/pricing.py::preco_efetivo roda como
-- agente_atendente (é chamada na hora de cobrar, dentro do fluxo de
-- atendimento) e precisa ler precificacao_historico pra saber se há desconto
-- aprovado vigente — GRANT que nunca existiu pra essa role (0011 só deu a
-- gerente_estoque, financeiro e orquestrador). SELECT completo (não
-- column-level): a tabela não tem dado sensível de cliente, é histórico de
-- preço/margem, mesmo padrão de acesso já concedido a lotes/estoque.
GRANT SELECT ON precificacao_historico TO agente_atendente;

CREATE POLICY sel_atendente ON precificacao_historico FOR SELECT TO agente_atendente USING (true);
