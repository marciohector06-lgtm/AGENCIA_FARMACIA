-- Seed de demonstração/piloto — MIPs (medicamentos isentos de prescrição) para
-- popular o Supabase de produção antes do teste com o Márcio. NÃO é uma
-- migration Alembic/numerada: é um script manual, feito pra ser colado no
-- SQL Editor do Supabase, fora da cadeia de versionamento de schema.
--
-- Idempotente por PK: todo INSERT usa um UUID fixo + ON CONFLICT (id) DO
-- NOTHING, então rodar este script de novo (ex.: depois de adicionar mais
-- produtos a mão) nunca duplica nem falha.
--
-- Filial: usa a que já existe, NÃO cria uma nova.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM filiais WHERE id = '6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2') THEN
    RAISE EXCEPTION 'Filial 6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2 não existe — confirme o UUID antes de rodar o resto do seed.';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Fabricantes (3)
-- ---------------------------------------------------------------------------
INSERT INTO fabricantes (id, nome, pais_origem) VALUES
  ('b0000000-0000-0000-0000-000000000001', 'EMS', 'Brasil'),
  ('b0000000-0000-0000-0000-000000000002', 'Medley', 'Brasil'),
  ('b0000000-0000-0000-0000-000000000003', 'Eurofarma', 'Brasil')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Princípios ativos (10, todos MIP)
--
-- Ranitidina: incluída porque foi pedida explicitamente, mas SEM nenhum
-- produto associado abaixo — a substância foi retirada do mercado global
-- (contaminação por NDMA, ~2020) e a ANVISA suspendeu registros. Manter só o
-- cadastro do princípio ativo (não é mentira dizer que ele existe como
-- classe), mas criar um "produto à venda" com ranitidina seria dado de
-- demonstração factualmente incorreto pra um sistema cujo objetivo é
-- justamente confiabilidade clínica. Se precisar de um 10º produto vendável,
-- troque por outro princípio ativo.
-- ---------------------------------------------------------------------------
INSERT INTO principios_ativos (id, nome, classe_terapeutica) VALUES
  ('c0000000-0000-0000-0000-000000000001', 'Paracetamol', 'Analgésico e antitérmico'),
  ('c0000000-0000-0000-0000-000000000002', 'Ibuprofeno', 'Anti-inflamatório não esteroidal'),
  ('c0000000-0000-0000-0000-000000000003', 'Dipirona', 'Analgésico e antitérmico'),
  ('c0000000-0000-0000-0000-000000000004', 'Loratadina', 'Anti-histamínico'),
  ('c0000000-0000-0000-0000-000000000005', 'Cetirizina', 'Anti-histamínico'),
  ('c0000000-0000-0000-0000-000000000006', 'Omeprazol', 'Inibidor de bomba de prótons'),
  ('c0000000-0000-0000-0000-000000000007', 'Ranitidina', 'Antagonista H2 (uso descontinuado — ver comentário acima)'),
  ('c0000000-0000-0000-0000-000000000008', 'Dextrometorfano', 'Antitussígeno'),
  ('c0000000-0000-0000-0000-000000000009', 'Guaifenesina', 'Expectorante'),
  ('c0000000-0000-0000-0000-000000000010', 'Escopolamina', 'Antiespasmódico')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Produtos (15, todos tarja='isento')
--
-- Nomes comerciais reais foram usados só onde o status MIP/isento é bem
-- estabelecido (Tylenol, Advil, Neosaldina, Buscopan) — os fabricantes reais
-- desses produtos NÃO são EMS/Medley/Eurofarma (são Kenvue/Haleon/Sanofi);
-- a atribuição abaixo é só pra ter dado de demo plausível dentro dos 3
-- fabricantes pedidos, não é cadastro real de fabricante-marca. Os demais
-- produtos usam o padrão real de genérico brasileiro "<Princípio Ativo>
-- <Fabricante> <concentração>".
-- ---------------------------------------------------------------------------
INSERT INTO produtos (
  id, principio_ativo_id, fabricante_id, nome_comercial,
  forma_farmaceutica, via_administracao, concentracao_valor, concentracao_unidade,
  quantidade_embalagem, tarja, preco_tabela, custo_medio
) VALUES
  ('d0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Tylenol 750mg', 'comprimido', 'oral', 750, 'mg', 20, 'isento', 24.90, 13.50),
  ('d0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Paracetamol Medley 500mg', 'comprimido', 'oral', 500, 'mg', 20, 'isento', 8.50, 4.20),
  ('d0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000003', 'Paracetamol Eurofarma 750mg', 'comprimido', 'oral', 750, 'mg', 10, 'isento', 9.90, 5.10),
  ('d0000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'Advil 400mg', 'capsula', 'oral', 400, 'mg', 20, 'isento', 26.90, 15.00),
  ('d0000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000003', 'Ibuprofeno Eurofarma 400mg', 'comprimido', 'oral', 400, 'mg', 20, 'isento', 12.90, 6.80),
  ('d0000000-0000-0000-0000-000000000006', 'c0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000002', 'Dipirona Sódica Medley 500mg', 'comprimido', 'oral', 500, 'mg', 10, 'isento', 6.90, 3.30),
  ('d0000000-0000-0000-0000-000000000007', 'c0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000003', 'Neosaldina 20 comprimidos', 'comprimido', 'oral', 300, 'mg', 20, 'isento', 19.90, 11.20),
  ('d0000000-0000-0000-0000-000000000008', 'c0000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001', 'Loratadina EMS 10mg', 'comprimido', 'oral', 10, 'mg', 12, 'isento', 14.90, 7.90),
  ('d0000000-0000-0000-0000-000000000009', 'c0000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000002', 'Cetirizina Medley 10mg', 'comprimido', 'oral', 10, 'mg', 10, 'isento', 13.50, 7.10),
  ('d0000000-0000-0000-0000-000000000010', 'c0000000-0000-0000-0000-000000000006', 'b0000000-0000-0000-0000-000000000001', 'Omeprazol EMS 20mg', 'capsula', 'oral', 20, 'mg', 14, 'isento', 17.90, 9.60),
  ('d0000000-0000-0000-0000-000000000011', 'c0000000-0000-0000-0000-000000000008', 'b0000000-0000-0000-0000-000000000003', 'Xarope Dextrometorfano Eurofarma', 'xarope', 'oral', 15, 'mg', 120, 'isento', 21.90, 12.30),
  ('d0000000-0000-0000-0000-000000000012', 'c0000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000002', 'Xarope Guaifenesina Medley', 'xarope', 'oral', 100, 'mg', 120, 'isento', 18.50, 10.40),
  ('d0000000-0000-0000-0000-000000000013', 'c0000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000001', 'Xarope Expectorante EMS', 'xarope', 'oral', 100, 'mg', 120, 'isento', 22.50, 12.80),
  ('d0000000-0000-0000-0000-000000000014', 'c0000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000001', 'Buscopan 10mg', 'comprimido', 'oral', 10, 'mg', 20, 'isento', 24.50, 14.10),
  ('d0000000-0000-0000-0000-000000000015', 'c0000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000003', 'Escopolamina Eurofarma 10mg', 'comprimido', 'oral', 10, 'mg', 10, 'isento', 15.90, 8.70)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Lotes (1 por produto) — validade sempre calculada a partir de CURRENT_DATE,
-- nunca uma data fixa, pra continuar "1 ano à frente" não importa quando este
-- script for rodado.
-- ---------------------------------------------------------------------------
INSERT INTO lotes (id, produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
SELECT
  ('e0000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  ('d0000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  'SEED-' || lpad(n::text, 3, '0'),
  CURRENT_DATE - INTERVAL '30 days',
  CURRENT_DATE + INTERVAL '1 year',
  100,
  p.custo_medio,
  'disponivel'
FROM generate_series(1, 15) AS n
JOIN produtos p ON p.id = ('d0000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Estoque (1 registro por lote, na filial existente, quantidade_atual=100)
-- ---------------------------------------------------------------------------
INSERT INTO estoque (id, filial_id, lote_id, quantidade_atual)
SELECT
  ('f0000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  '6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2',
  ('e0000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  100
FROM generate_series(1, 15) AS n
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Conferência rápida pós-seed
-- ---------------------------------------------------------------------------
SELECT
  (SELECT count(*) FROM fabricantes WHERE id::text LIKE 'b0000000%') AS fabricantes_seed,
  (SELECT count(*) FROM principios_ativos WHERE id::text LIKE 'c0000000%') AS principios_ativos_seed,
  (SELECT count(*) FROM produtos WHERE id::text LIKE 'd0000000%' AND tarja = 'isento') AS produtos_isento_seed,
  (SELECT count(*) FROM lotes WHERE id::text LIKE 'e0000000%') AS lotes_seed,
  (SELECT count(*) FROM estoque WHERE id::text LIKE 'f0000000%' AND quantidade_atual = 100) AS estoque_seed;
