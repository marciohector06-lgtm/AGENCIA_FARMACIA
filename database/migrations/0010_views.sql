-- FASE 1: Views de leitura que os agentes vão consumir como "tools" a partir da FASE 3.

-- Posição de estoque consolidada por lote/filial, já com dias até o vencimento.
CREATE OR REPLACE VIEW vw_estoque_atual AS
SELECT
    e.id AS estoque_id,
    f.id AS filial_id,
    f.nome AS filial_nome,
    p.id AS produto_id,
    p.nome_comercial,
    p.tarja,
    l.id AS lote_id,
    l.numero_lote,
    l.data_validade,
    (l.data_validade - CURRENT_DATE) AS dias_para_vencer,
    e.quantidade_atual,
    e.quantidade_reservada,
    (e.quantidade_atual - e.quantidade_reservada) AS quantidade_disponivel,
    l.status
FROM estoque e
JOIN lotes l ON l.id = e.lote_id
JOIN produtos p ON p.id = l.produto_id
JOIN filiais f ON f.id = e.filial_id;

-- Pares de produtos permutáveis: mesmo princípio ativo, mesma forma farmacêutica
-- e mesma via de administração, restrito a MIPs ativos. É a base da sugestão
-- de similar do Agente Atendente (regra "Zero Alucinação Clínica").
CREATE OR REPLACE VIEW vw_produtos_substituiveis AS
SELECT
    p1.id AS produto_origem_id,
    p1.nome_comercial AS produto_origem_nome,
    p2.id AS produto_substituto_id,
    p2.nome_comercial AS produto_substituto_nome,
    p1.principio_ativo_id,
    p1.concentracao_valor AS concentracao_origem,
    p2.concentracao_valor AS concentracao_substituto,
    p1.concentracao_unidade
FROM produtos p1
JOIN produtos p2
    ON p2.principio_ativo_id = p1.principio_ativo_id
    AND p2.forma_farmaceutica = p1.forma_farmaceutica
    AND p2.via_administracao = p1.via_administracao
    AND p2.id <> p1.id
WHERE p1.tarja = 'isento'
    AND p2.tarja = 'isento'
    AND p1.ativo = true
    AND p2.ativo = true;

-- Giro de vendas dos últimos 90 dias por produto, insumo para Curva ABC
-- e predição de demanda do Agente Gerente de Estoque.
CREATE OR REPLACE VIEW vw_giro_estoque_90d AS
SELECT
    vi.produto_id,
    SUM(vi.quantidade) AS unidades_vendidas_90d,
    COUNT(DISTINCT v.id) AS numero_vendas_90d,
    ROUND(SUM(vi.subtotal), 2) AS receita_90d
FROM vendas_itens vi
JOIN vendas v ON v.id = vi.venda_id
WHERE v.data_venda >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY vi.produto_id;
