-- FASE 1: Índices de suporte às consultas mais frequentes dos agentes
-- (join de estoque/lotes, checagem de validade, giro de vendas).

CREATE INDEX IF NOT EXISTS idx_produtos_principio_ativo ON produtos (principio_ativo_id);
CREATE INDEX IF NOT EXISTS idx_produtos_tarja_ativo ON produtos (tarja, ativo);
CREATE INDEX IF NOT EXISTS idx_produtos_forma_via ON produtos (forma_farmaceutica, via_administracao);

CREATE INDEX IF NOT EXISTS idx_lotes_produto ON lotes (produto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_data_validade ON lotes (data_validade);
CREATE INDEX IF NOT EXISTS idx_lotes_status ON lotes (status);

CREATE INDEX IF NOT EXISTS idx_estoque_filial ON estoque (filial_id);
CREATE INDEX IF NOT EXISTS idx_estoque_lote ON estoque (lote_id);

CREATE INDEX IF NOT EXISTS idx_vendas_itens_produto ON vendas_itens (produto_id);
CREATE INDEX IF NOT EXISTS idx_vendas_itens_venda ON vendas_itens (venda_id);
CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas (data_venda);

CREATE INDEX IF NOT EXISTS idx_interacoes_a ON interacoes_medicamentosas (principio_ativo_a_id);
CREATE INDEX IF NOT EXISTS idx_interacoes_b ON interacoes_medicamentosas (principio_ativo_b_id);
CREATE INDEX IF NOT EXISTS idx_restricoes_principio_ativo ON restricoes_uso_principio_ativo (principio_ativo_id);

CREATE INDEX IF NOT EXISTS idx_precificacao_produto ON precificacao_historico (produto_id);
CREATE INDEX IF NOT EXISTS idx_precificacao_status ON precificacao_historico (status_aprovacao);
