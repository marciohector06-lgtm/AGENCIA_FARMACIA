-- Seed completo de farmácia de médio porte — Supabase de produção.
-- Script manual (SQL Editor), fora da cadeia versionada do Alembic, igual
-- seed_demo_mip.sql. Idempotente por PK: todo INSERT usa UUID fixo +
-- ON CONFLICT (id) DO NOTHING.
--
-- ==============================================================================
-- DESVIOS DO PEDIDO ORIGINAL — leia antes de rodar
-- ==============================================================================
-- 1) 7 produtos pedidos são tarja vermelha de verdade (pesquisado, não hipótese):
--      Nisulid (nimesulida)      — hepatotoxicidade
--      Plasil (metoclopramida)   — tarja vermelha com retenção de receita
--      Motigut (domperidona)     — risco cardíaco (QT longo)
--      Digesan (bromoprida)      — mesma classe/risco de metoclopramida
--      Fluconazol 150mg          — exige receita mesmo em dose única (não é MIP)
--      Furacin tópico (nitrofural) — tarja vermelha
--      Trimedal                 — vendido sob prescrição médica
--    Nenhum desses vira produto. Os princípios ativos correspondentes (quando
--    pedidos: nimesulida, metoclopramida, domperidona, bromoprida, fluconazol)
--    ainda são cadastrados — servem pra checar interação/restrição quando um
--    cliente relata usar um remédio controlado, mesmo que a farmácia não venda.
--
-- 2) 8 princípios ativos extras (fora dos 20 pedidos), só-referência, nunca
--    viram produto — necessários porque os pares de interação pedidos citam
--    substâncias/classes que não têm nenhuma outra linha no catálogo:
--    Varfarina, Álcool etílico, Ferro, Clopidogrel, Inibidores da MAO (classe),
--    Anti-hipertensivos (classe), Antipsicóticos (classe), e um princípio
--    "Probióticos" genérico (organismos vivos não se encaixam bem no desenho
--    de "princípio ativo" farmacológico da tabela, mas os produtos probióticos
--    pedidos precisam de um FK).
--
-- 3) Produtos combinados (ex.: Benegrip, Resfenol) ficam ligados a UM princípio
--    ativo "primário" — o schema (produtos.principio_ativo_id) não suporta
--    múltiplos ativos por produto. Mesma simplificação já usada no seed anterior
--    (Neosaldina → Dipirona).
--
-- 4) ~46 dos produtos abaixo são genéricos "<Princípio Ativo> <Fabricante>
--    <concentração>" pra fechar o mínimo de 80 sem arriscar mais classificação
--    de marca — é o padrão mais seguro (genérico de princípio já confirmado
--    isento é sempre isento).
--
-- 5) Algumas restrições pedidas não têm campo no enum tipo_restricao_enum
--    (gestante/lactante/pediatrico/idoso/insuficiencia_renal/insuficiencia_
--    hepatica/hipertenso/diabetico) — não existe "úlcera péptica",
--    "cardiopata", "Parkinson", "alcoolismo" ou "operador de máquinas". Essas
--    ficaram de fora (não dá pra representar sem inventar valor de enum).
-- ==============================================================================

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM filiais WHERE id = '6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2') THEN
    RAISE EXCEPTION 'Filial 6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2 não existe.';
  END IF;
  IF (SELECT count(*) FROM produtos WHERE id::text LIKE 'd0000000%') < 15 THEN
    RAISE EXCEPTION 'Os 15 produtos do seed anterior (d0000000-*) não foram encontrados — rode seed_demo_mip.sql primeiro.';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Fabricantes novos (10)
-- ---------------------------------------------------------------------------
INSERT INTO fabricantes (id, nome, pais_origem) VALUES
  ('b1000000-0000-0000-0000-000000000001', 'Aché', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000002', 'Bayer', 'Alemanha'),
  ('b1000000-0000-0000-0000-000000000003', 'Pfizer', 'Estados Unidos'),
  ('b1000000-0000-0000-0000-000000000004', 'Sanofi', 'França'),
  ('b1000000-0000-0000-0000-000000000005', 'Hypera Pharma', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000006', 'Neo Química', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000007', 'Cimed', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000008', 'Legrand Pharma', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000009', 'União Química', 'Brasil'),
  ('b1000000-0000-0000-0000-000000000010', 'Farmacêutica Serena', 'Brasil')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Princípios ativos — 20 pedidos (MIP quando indicado; 5 deles são tarja
-- vermelha na vida real e ficam SEM produto associado, ver nota 1 acima).
-- ---------------------------------------------------------------------------
INSERT INTO principios_ativos (id, nome, classe_terapeutica, contraindicacoes_gerais) VALUES
  ('c1000000-0000-0000-0000-000000000001', 'Dexclorfeniramina', 'Anti-histamínico', NULL),
  ('c1000000-0000-0000-0000-000000000002', 'Pseudoefedrina', 'Descongestionante nasal', NULL),
  ('c1000000-0000-0000-0000-000000000003', 'Nimesulida', 'Anti-inflamatório não esteroidal', 'Tarja vermelha no Brasil (risco de hepatotoxicidade) — não vendido nesta farmácia, cadastrado só para checagem de interação/restrição.'),
  ('c1000000-0000-0000-0000-000000000004', 'Naproxeno', 'Anti-inflamatório não esteroidal', NULL),
  ('c1000000-0000-0000-0000-000000000005', 'Ácido acetilsalicílico', 'Analgésico, antitérmico e antiagregante plaquetário', NULL),
  ('c1000000-0000-0000-0000-000000000006', 'Bromoprida', 'Antiemético/procinético', 'Tarja vermelha no Brasil — não vendido nesta farmácia, cadastrado só para checagem de interação/restrição.'),
  ('c1000000-0000-0000-0000-000000000007', 'Domperidona', 'Antiemético/procinético', 'Tarja vermelha no Brasil (risco cardíaco/QT longo) — não vendido nesta farmácia, cadastrado só para checagem de interação/restrição.'),
  ('c1000000-0000-0000-0000-000000000008', 'Metoclopramida', 'Antiemético/procinético', 'Tarja vermelha no Brasil, com retenção de receita — não vendido nesta farmácia, cadastrado só para checagem de interação/restrição.'),
  ('c1000000-0000-0000-0000-000000000009', 'Simeticona', 'Antiflatulento', NULL),
  ('c1000000-0000-0000-0000-000000000010', 'Carbonato de cálcio', 'Antiácido e suplemento mineral', NULL),
  ('c1000000-0000-0000-0000-000000000011', 'Hidróxido de alumínio', 'Antiácido', NULL),
  ('c1000000-0000-0000-0000-000000000012', 'Hidróxido de magnésio', 'Antiácido e laxante', NULL),
  ('c1000000-0000-0000-0000-000000000013', 'Vitamina C', 'Vitamina/suplemento', NULL),
  ('c1000000-0000-0000-0000-000000000014', 'Vitamina D', 'Vitamina/suplemento', NULL),
  ('c1000000-0000-0000-0000-000000000015', 'Complexo B', 'Vitamina/suplemento', NULL),
  ('c1000000-0000-0000-0000-000000000016', 'Zinco', 'Suplemento mineral', NULL),
  ('c1000000-0000-0000-0000-000000000017', 'Melatonina', 'Indutor do sono', NULL),
  ('c1000000-0000-0000-0000-000000000018', 'Própolis', 'Fitoterápico/imunomodulador', NULL),
  ('c1000000-0000-0000-0000-000000000019', 'Fluconazol', 'Antifúngico sistêmico', 'Exige receita médica no Brasil mesmo em dose única de 150mg — não vendido nesta farmácia, cadastrado só para checagem de interação/restrição.'),
  ('c1000000-0000-0000-0000-000000000020', 'Miconazol', 'Antifúngico tópico', NULL)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Princípios ativos extras, só-referência (ver nota 2) — nunca viram produto.
-- ---------------------------------------------------------------------------
INSERT INTO principios_ativos (id, nome, classe_terapeutica, contraindicacoes_gerais) VALUES
  ('c1000001-0000-0000-0000-000000000001', 'Varfarina', 'Anticoagulante (referência)', 'Não vendido nesta farmácia (tarja vermelha, uso monitorado) — cadastrado só para checagem de interação.'),
  ('c1000001-0000-0000-0000-000000000002', 'Álcool etílico', 'Referência (interação)', 'Não é um medicamento — cadastrado só para checagem de interação com álcool.'),
  ('c1000001-0000-0000-0000-000000000003', 'Ferro (sulfato ferroso)', 'Suplemento mineral (referência)', NULL),
  ('c1000001-0000-0000-0000-000000000004', 'Clopidogrel', 'Antiagregante plaquetário (referência)', 'Não vendido nesta farmácia (tarja vermelha) — cadastrado só para checagem de interação.'),
  ('c1000001-0000-0000-0000-000000000005', 'Inibidores da MAO (classe)', 'Referência (interação, classe terapêutica)', 'Entrada de classe, não substância única — não vendido nesta farmácia.'),
  ('c1000001-0000-0000-0000-000000000006', 'Anti-hipertensivos (classe)', 'Referência (interação, classe terapêutica)', 'Entrada de classe, não substância única — não vendido nesta farmácia.'),
  ('c1000001-0000-0000-0000-000000000007', 'Antipsicóticos (classe)', 'Referência (interação, classe terapêutica)', 'Entrada de classe, não substância única — não vendido nesta farmácia.'),
  ('c1000001-0000-0000-0000-000000000008', 'Probióticos (Saccharomyces/Lactobacillus)', 'Probiótico', 'Organismo vivo, não princípio ativo farmacológico convencional — entrada simplificada só para linkar os produtos probióticos ao catálogo.')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Produtos novos (todos tarja='isento' — ver nota 1 sobre os excluídos).
-- Nomes reais só onde a classificação MIP é bem estabelecida; combinados
-- ligados a UM princípio ativo primário (ver nota 3); genéricos preenchem o
-- volume com segurança (ver nota 4).
-- ---------------------------------------------------------------------------
INSERT INTO produtos (
  id, principio_ativo_id, fabricante_id, nome_comercial,
  forma_farmaceutica, via_administracao, concentracao_valor, concentracao_unidade,
  quantidade_embalagem, tarja, preco_tabela, custo_medio
) VALUES
  -- Antigripais e descongestionantes (4)
  ('d1000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000005', 'Benegrip', 'comprimido', 'oral', 500, 'mg', 10, 'isento', 14.90, 8.20),
  ('d1000000-0000-0000-0000-000000000002', 'c1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000005', 'Resfenol', 'comprimido', 'oral', 2, 'mg', 16, 'isento', 16.90, 9.40),
  ('d1000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000006', 'Coristina D', 'comprimido', 'oral', 500, 'mg', 16, 'isento', 15.50, 8.60),
  ('d1000000-0000-0000-0000-000000000004', 'c1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000004', 'Naldecon', 'comprimido', 'oral', 30, 'mg', 12, 'isento', 18.90, 10.50),
  -- Antialérgicos (4)
  ('d1000000-0000-0000-0000-000000000005', 'c1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000004', 'Polaramine', 'comprimido', 'oral', 2, 'mg', 10, 'isento', 12.90, 7.10),
  ('d1000000-0000-0000-0000-000000000006', 'c0000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000003', 'Claritin', 'comprimido', 'oral', 10, 'mg', 12, 'isento', 22.90, 12.80),
  ('d1000000-0000-0000-0000-000000000007', 'c0000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000003', 'Zyrtec', 'comprimido', 'oral', 10, 'mg', 10, 'isento', 24.90, 13.90),
  ('d1000000-0000-0000-0000-000000000008', 'c0000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000009', 'Histadin', 'comprimido', 'oral', 10, 'mg', 12, 'isento', 15.90, 8.80),
  -- Anti-inflamatórios MIP (3)
  ('d1000000-0000-0000-0000-000000000009', 'c1000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000001', 'Flanax', 'comprimido', 'oral', 275, 'mg', 10, 'isento', 17.90, 9.90),
  ('d1000000-0000-0000-0000-000000000010', 'c1000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000002', 'AAS 100mg', 'comprimido', 'oral', 100, 'mg', 30, 'isento', 9.90, 5.20),
  ('d1000000-0000-0000-0000-000000000011', 'c1000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000002', 'Aspirina 500mg', 'comprimido', 'oral', 500, 'mg', 20, 'isento', 12.50, 6.80),
  -- Antiácidos e digestivos (3) — Digesan/Motigut ficaram de fora, ver nota 1
  ('d1000000-0000-0000-0000-000000000012', 'c1000000-0000-0000-0000-000000000010', 'b1000000-0000-0000-0000-000000000002', 'Eno', 'po', 'oral', 5, 'g', 6, 'isento', 11.90, 6.40),
  ('d1000000-0000-0000-0000-000000000013', 'c1000000-0000-0000-0000-000000000012', 'b1000000-0000-0000-0000-000000000007', 'Sonrisal', 'comprimido', 'oral', 1, 'g', 12, 'isento', 10.90, 5.90),
  ('d1000000-0000-0000-0000-000000000014', 'c1000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000005', 'Luftal', 'comprimido', 'oral', 40, 'mg', 20, 'isento', 19.90, 11.00),
  -- Antifúngicos MIP (3) — Fluconazol ficou de fora, ver nota 1
  ('d1000000-0000-0000-0000-000000000015', 'c1000000-0000-0000-0000-000000000020', 'b1000000-0000-0000-0000-000000000002', 'Canesten', 'creme', 'topica', 1, 'pct', 20, 'isento', 24.90, 13.80),
  ('d1000000-0000-0000-0000-000000000016', 'c1000000-0000-0000-0000-000000000020', 'b1000000-0000-0000-0000-000000000002', 'Gyno-Canesten', 'creme', 'vaginal', 2, 'pct', 1, 'isento', 32.90, 18.20),
  ('d1000000-0000-0000-0000-000000000017', 'c1000000-0000-0000-0000-000000000020', 'b1000000-0000-0000-0000-000000000003', 'Daktarin', 'creme', 'topica', 2, 'pct', 20, 'isento', 28.90, 16.00),
  -- Vitaminas e suplementos (5)
  ('d1000000-0000-0000-0000-000000000018', 'c1000000-0000-0000-0000-000000000013', 'b1000000-0000-0000-0000-000000000004', 'Cebion', 'comprimido', 'oral', 1, 'g', 10, 'isento', 18.90, 10.40),
  ('d1000000-0000-0000-0000-000000000019', 'c1000000-0000-0000-0000-000000000013', 'b1000000-0000-0000-0000-000000000002', 'Redoxon', 'comprimido', 'oral', 1, 'g', 10, 'isento', 21.90, 12.10),
  ('d1000000-0000-0000-0000-000000000020', 'c1000000-0000-0000-0000-000000000015', 'b1000000-0000-0000-0000-000000000003', 'Centrum', 'comprimido', 'oral', 1, 'pct', 30, 'isento', 59.90, 33.50),
  ('d1000000-0000-0000-0000-000000000021', 'c1000000-0000-0000-0000-000000000014', 'b1000000-0000-0000-0000-000000000004', 'Supradyn', 'comprimido', 'oral', 1, 'pct', 30, 'isento', 54.90, 30.60),
  ('d1000000-0000-0000-0000-000000000022', 'c1000000-0000-0000-0000-000000000016', 'b1000000-0000-0000-0000-000000000006', 'Avert', 'comprimido', 'oral', 10, 'mg', 30, 'isento', 34.90, 19.40),
  -- Analgésicos adicionais (2) — Neosaldina já existe no seed anterior
  ('d1000000-0000-0000-0000-000000000023', 'c0000000-0000-0000-0000-000000000010', 'b1000000-0000-0000-0000-000000000004', 'Buscopan Composto', 'comprimido', 'oral', 10, 'mg', 20, 'isento', 27.90, 15.50),
  ('d1000000-0000-0000-0000-000000000024', 'c0000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000004', 'Dorico', 'comprimido', 'oral', 750, 'mg', 10, 'isento', 16.90, 9.30),
  -- Xaropes e expectorantes (4)
  ('d1000000-0000-0000-0000-000000000025', 'c0000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000002', 'Bisolvon', 'xarope', 'oral', 8, 'mg', 120, 'isento', 23.90, 13.30),
  ('d1000000-0000-0000-0000-000000000026', 'c0000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000004', 'Mucosolvan', 'xarope', 'oral', 30, 'mg', 120, 'isento', 25.90, 14.40),
  ('d1000000-0000-0000-0000-000000000027', 'c0000000-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000005', 'Vick 44', 'xarope', 'oral', 15, 'mg', 120, 'isento', 22.90, 12.70),
  ('d1000000-0000-0000-0000-000000000028', 'c0000000-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000003', 'Vibral', 'xarope', 'oral', 3, 'mg', 120, 'isento', 21.90, 12.20),
  -- Pomadas e uso tópico (3) — Furacin ficou de fora; sem principio_ativo (produto não-sistêmico, ver schema)
  ('d1000000-0000-0000-0000-000000000029', NULL, 'b1000000-0000-0000-0000-000000000004', 'Bepantol', 'pomada', 'topica', 50, 'mg', 30, 'isento', 26.90, 14.90),
  ('d1000000-0000-0000-0000-000000000030', NULL, 'b1000000-0000-0000-0000-000000000005', 'Hipoglós', 'pomada', 'topica', 1, 'pct', 45, 'isento', 19.90, 11.00),
  ('d1000000-0000-0000-0000-000000000031', NULL, 'b1000000-0000-0000-0000-000000000005', 'Dersani', 'creme', 'topica', 1, 'pct', 100, 'isento', 24.90, 13.80),
  -- Colírios MIP (3) — lubrificantes, sem principio_ativo sistêmico
  ('d1000000-0000-0000-0000-000000000032', NULL, 'b1000000-0000-0000-0000-000000000003', 'Systane', 'colirio', 'oftalmica', 10, 'ml', 1, 'isento', 32.90, 18.20),
  ('d1000000-0000-0000-0000-000000000033', NULL, 'b1000000-0000-0000-0000-000000000009', 'Lacrifilm', 'colirio', 'oftalmica', 15, 'ml', 1, 'isento', 24.90, 13.80),
  ('d1000000-0000-0000-0000-000000000034', NULL, 'b1000000-0000-0000-0000-000000000007', 'Lacrima Plus', 'colirio', 'oftalmica', 15, 'ml', 1, 'isento', 22.90, 12.70),
  -- Laxantes MIP (3)
  ('d1000000-0000-0000-0000-000000000035', 'c1000000-0000-0000-0000-000000000012', 'b1000000-0000-0000-0000-000000000002', 'Dulcolax', 'comprimido', 'oral', 5, 'mg', 20, 'isento', 21.90, 12.20),
  ('d1000000-0000-0000-0000-000000000036', 'c1000000-0000-0000-0000-000000000012', 'b1000000-0000-0000-0000-000000000005', 'Lactulose Xarope', 'xarope', 'oral', 667, 'mg', 120, 'isento', 26.90, 14.90),
  ('d1000000-0000-0000-0000-000000000037', NULL, 'b1000000-0000-0000-0000-000000000003', 'Metamucil', 'po', 'oral', 1, 'pct', 30, 'isento', 44.90, 25.00),
  -- Probióticos (3)
  ('d1000000-0000-0000-0000-000000000038', 'c1000001-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000004', 'Floratil', 'po', 'oral', 200, 'mg', 5, 'isento', 29.90, 16.60),
  ('d1000000-0000-0000-0000-000000000039', 'c1000001-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000004', 'Enterogermina', 'solucao', 'oral', 2, 'ml', 5, 'isento', 34.90, 19.40),
  ('d1000000-0000-0000-0000-000000000040', 'c1000001-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000007', 'Lactobacillus Comprimido', 'comprimido', 'oral', 1, 'ui', 30, 'isento', 27.90, 15.50),
  -- Genéricos adicionais (fecham o volume com segurança — ver nota 4)
  ('d1000000-0000-0000-0000-000000000041', 'c0000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000006', 'Paracetamol Neo Química 750mg', 'comprimido', 'oral', 750, 'mg', 20, 'isento', 7.90, 3.90),
  ('d1000000-0000-0000-0000-000000000042', 'c0000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000006', 'Ibuprofeno Neo Química 600mg', 'comprimido', 'oral', 600, 'mg', 20, 'isento', 15.90, 8.80),
  ('d1000000-0000-0000-0000-000000000043', 'c0000000-0000-0000-0000-000000000003', 'b1000000-0000-0000-0000-000000000007', 'Dipirona Cimed 1g', 'comprimido', 'oral', 1000, 'mg', 10, 'isento', 7.50, 3.70),
  ('d1000000-0000-0000-0000-000000000044', 'c0000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000007', 'Loratadina Cimed 10mg', 'comprimido', 'oral', 10, 'mg', 12, 'isento', 9.90, 5.20),
  ('d1000000-0000-0000-0000-000000000045', 'c0000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000009', 'Cetirizina União Química 10mg', 'comprimido', 'oral', 10, 'mg', 10, 'isento', 10.90, 5.70),
  ('d1000000-0000-0000-0000-000000000046', 'c0000000-0000-0000-0000-000000000006', 'b1000000-0000-0000-0000-000000000009', 'Omeprazol União Química 20mg', 'capsula', 'oral', 20, 'mg', 28, 'isento', 22.90, 12.70),
  ('d1000000-0000-0000-0000-000000000047', 'c1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000010', 'Dexclorfeniramina Serena 2mg', 'comprimido', 'oral', 2, 'mg', 20, 'isento', 8.90, 4.60),
  ('d1000000-0000-0000-0000-000000000048', 'c1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000010', 'Pseudoefedrina Serena 60mg', 'comprimido', 'oral', 60, 'mg', 12, 'isento', 13.90, 7.60),
  ('d1000000-0000-0000-0000-000000000049', 'c1000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000008', 'Naproxeno Legrand 275mg', 'comprimido', 'oral', 275, 'mg', 10, 'isento', 12.90, 6.90),
  ('d1000000-0000-0000-0000-000000000050', 'c1000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000008', 'AAS Legrand 500mg', 'comprimido', 'oral', 500, 'mg', 20, 'isento', 10.90, 5.70),
  ('d1000000-0000-0000-0000-000000000051', 'c1000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000001', 'Simeticona Aché 40mg', 'comprimido', 'oral', 40, 'mg', 20, 'isento', 16.90, 9.30),
  ('d1000000-0000-0000-0000-000000000052', 'c1000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000001', 'Simeticona Aché Gotas', 'solucao', 'oral', 75, 'mg', 15, 'isento', 18.90, 10.50),
  ('d1000000-0000-0000-0000-000000000053', 'c1000000-0000-0000-0000-000000000010', 'b1000000-0000-0000-0000-000000000001', 'Carbonato de Cálcio Aché 500mg', 'comprimido', 'oral', 500, 'mg', 30, 'isento', 14.90, 8.20),
  ('d1000000-0000-0000-0000-000000000054', 'c1000000-0000-0000-0000-000000000011', 'b1000000-0000-0000-0000-000000000006', 'Hidróxido de Alumínio Neo Química', 'suspensao', 'oral', 60, 'mg', 100, 'isento', 13.90, 7.60),
  ('d1000000-0000-0000-0000-000000000055', 'c1000000-0000-0000-0000-000000000012', 'b1000000-0000-0000-0000-000000000006', 'Hidróxido de Magnésio Neo Química', 'suspensao', 'oral', 60, 'mg', 100, 'isento', 12.90, 7.10),
  ('d1000000-0000-0000-0000-000000000056', 'c1000000-0000-0000-0000-000000000013', 'b1000000-0000-0000-0000-000000000007', 'Vitamina C Cimed 500mg', 'comprimido', 'oral', 500, 'mg', 30, 'isento', 13.90, 7.60),
  ('d1000000-0000-0000-0000-000000000057', 'c1000000-0000-0000-0000-000000000013', 'b1000000-0000-0000-0000-000000000009', 'Vitamina C União Química 1g Efervescente', 'comprimido', 'oral', 1000, 'mg', 10, 'isento', 17.90, 9.90),
  ('d1000000-0000-0000-0000-000000000058', 'c1000000-0000-0000-0000-000000000014', 'b1000000-0000-0000-0000-000000000007', 'Vitamina D Cimed 2000ui', 'comprimido', 'oral', 2000, 'ui', 30, 'isento', 24.90, 13.80),
  ('d1000000-0000-0000-0000-000000000059', 'c1000000-0000-0000-0000-000000000014', 'b1000000-0000-0000-0000-000000000009', 'Vitamina D União Química Gotas', 'solucao', 'oral', 200, 'ui', 10, 'isento', 29.90, 16.60),
  ('d1000000-0000-0000-0000-000000000060', 'c1000000-0000-0000-0000-000000000015', 'b1000000-0000-0000-0000-000000000010', 'Complexo B Serena', 'comprimido', 'oral', 1, 'pct', 30, 'isento', 15.90, 8.80),
  ('d1000000-0000-0000-0000-000000000061', 'c1000000-0000-0000-0000-000000000016', 'b1000000-0000-0000-0000-000000000001', 'Zinco Aché 25mg', 'comprimido', 'oral', 25, 'mg', 30, 'isento', 19.90, 11.00),
  ('d1000000-0000-0000-0000-000000000062', 'c1000000-0000-0000-0000-000000000016', 'b1000000-0000-0000-0000-000000000006', 'Zinco Neo Química 50mg', 'comprimido', 'oral', 50, 'mg', 30, 'isento', 21.90, 12.10),
  ('d1000000-0000-0000-0000-000000000063', 'c1000000-0000-0000-0000-000000000017', 'b1000000-0000-0000-0000-000000000001', 'Melatonina Aché 0,21mg', 'comprimido', 'sublingual', 0.21, 'mg', 30, 'isento', 32.90, 18.20),
  ('d1000000-0000-0000-0000-000000000064', 'c1000000-0000-0000-0000-000000000017', 'b1000000-0000-0000-0000-000000000007', 'Melatonina Cimed 0,21mg', 'comprimido', 'sublingual', 0.21, 'mg', 30, 'isento', 29.90, 16.60),
  ('d1000000-0000-0000-0000-000000000065', 'c1000000-0000-0000-0000-000000000018', 'b1000000-0000-0000-0000-000000000001', 'Própolis Aché Extrato', 'solucao', 'oral', 30, 'ml', 1, 'isento', 27.90, 15.50),
  ('d1000000-0000-0000-0000-000000000066', 'c1000000-0000-0000-0000-000000000018', 'b1000000-0000-0000-0000-000000000010', 'Própolis Serena Comprimido', 'comprimido', 'oral', 300, 'mg', 30, 'isento', 23.90, 13.30),
  ('d1000000-0000-0000-0000-000000000067', 'c1000000-0000-0000-0000-000000000020', 'b1000000-0000-0000-0000-000000000006', 'Miconazol Neo Química Creme', 'creme', 'topica', 2, 'pct', 28, 'isento', 19.90, 11.00),
  ('d1000000-0000-0000-0000-000000000068', 'c1000000-0000-0000-0000-000000000020', 'b1000000-0000-0000-0000-000000000009', 'Miconazol União Química Pó', 'po', 'topica', 2, 'pct', 30, 'isento', 17.90, 9.90),
  ('d1000000-0000-0000-0000-000000000069', 'c0000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000008', 'Guaifenesina Legrand Xarope', 'xarope', 'oral', 100, 'mg', 120, 'isento', 18.90, 10.50),
  ('d1000000-0000-0000-0000-000000000070', 'c0000000-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000008', 'Dextrometorfano Legrand Xarope', 'xarope', 'oral', 15, 'mg', 120, 'isento', 19.90, 11.00),
  ('d1000000-0000-0000-0000-000000000071', 'c0000000-0000-0000-0000-000000000010', 'b1000000-0000-0000-0000-000000000010', 'Escopolamina Serena 10mg', 'comprimido', 'oral', 10, 'mg', 20, 'isento', 14.90, 8.20),
  ('d1000000-0000-0000-0000-000000000072', 'c0000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000003', 'Paracetamol Pfizer Gotas', 'solucao', 'oral', 200, 'mg', 15, 'isento', 12.90, 7.10),
  ('d1000000-0000-0000-0000-000000000073', 'c0000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000002', 'Ibuprofeno Bayer 400mg', 'comprimido', 'oral', 400, 'mg', 20, 'isento', 17.90, 9.90),
  ('d1000000-0000-0000-0000-000000000074', 'c1000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000002', 'Naproxeno Bayer 550mg', 'comprimido', 'oral', 550, 'mg', 10, 'isento', 21.90, 12.10),
  ('d1000000-0000-0000-0000-000000000075', 'c1000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000002', 'AAS Prevent 100mg', 'comprimido', 'oral', 100, 'mg', 30, 'isento', 11.90, 6.30),
  ('d1000000-0000-0000-0000-000000000076', 'c0000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000005', 'Loratadina Hypera Xarope', 'xarope', 'oral', 1, 'mg', 100, 'isento', 16.90, 9.40),
  ('d1000000-0000-0000-0000-000000000077', 'c0000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000005', 'Cetirizina Hypera Gotas', 'solucao', 'oral', 10, 'mg', 20, 'isento', 15.90, 8.80),
  ('d1000000-0000-0000-0000-000000000078', 'c1000000-0000-0000-0000-000000000010', 'b1000000-0000-0000-0000-000000000009', 'Carbonato de Cálcio União Química + Vit D', 'comprimido', 'oral', 600, 'mg', 60, 'isento', 26.90, 14.90),
  ('d1000000-0000-0000-0000-000000000079', 'c1000000-0000-0000-0000-000000000013', 'b1000000-0000-0000-0000-000000000006', 'Vitamina C Neo Química Mastigável', 'comprimido', 'oral', 500, 'mg', 30, 'isento', 12.90, 6.90),
  ('d1000000-0000-0000-0000-000000000080', 'c1000000-0000-0000-0000-000000000016', 'b1000000-0000-0000-0000-000000000010', 'Zinco Serena Gotas', 'solucao', 'oral', 4, 'mg', 30, 'isento', 22.90, 12.70),
  ('d1000000-0000-0000-0000-000000000081', 'c0000000-0000-0000-0000-000000000006', 'b1000000-0000-0000-0000-000000000001', 'Omeprazol Aché 20mg', 'capsula', 'oral', 20, 'mg', 14, 'isento', 15.90, 8.80),
  ('d1000000-0000-0000-0000-000000000082', 'c0000000-0000-0000-0000-000000000003', 'b1000000-0000-0000-0000-000000000004', 'Dipirona Sanofi Gotas', 'solucao', 'oral', 500, 'mg', 20, 'isento', 11.90, 6.30),
  ('d1000000-0000-0000-0000-000000000083', 'c1000000-0000-0000-0000-000000000009', 'b1000000-0000-0000-0000-000000000007', 'Simeticona Cimed Gotas Pediátrica', 'solucao', 'oral', 75, 'mg', 10, 'isento', 15.90, 8.80),
  ('d1000000-0000-0000-0000-000000000084', 'c1000000-0000-0000-0000-000000000018', 'b1000000-0000-0000-0000-000000000006', 'Própolis Neo Química Spray', 'spray', 'oral', 30, 'ml', 1, 'isento', 25.90, 14.40),
  ('d1000000-0000-0000-0000-000000000085', 'c1000000-0000-0000-0000-000000000012', 'b1000000-0000-0000-0000-000000000004', 'Hidróxido de Magnésio Sanofi (Leite de Magnésia)', 'suspensao', 'oral', 80, 'mg', 200, 'isento', 16.90, 9.40),
  ('d1000000-0000-0000-0000-000000000086', 'c0000000-0000-0000-0000-000000000007', 'b1000000-0000-0000-0000-000000000003', 'Fexofenadina Pfizer 180mg', 'comprimido', 'oral', 180, 'mg', 10, 'isento', 26.90, 14.90)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Interações medicamentosas (15 pares únicos — o pedido tinha "Ibuprofeno +
-- AAS" e "AAS + Ibuprofeno" como o MESMO par; contei uma vez e completei com
-- "Cálcio + Zinco" pra fechar 15, ver nota abaixo do INSERT).
-- Ordem canônica (a_id < b_id) calculada a partir dos UUIDs reais.
-- ---------------------------------------------------------------------------
INSERT INTO interacoes_medicamentosas (id, principio_ativo_a_id, principio_ativo_b_id, gravidade, descricao) VALUES
  ('a2000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'c1000000-0000-0000-0000-000000000005', 'moderada', 'Uso conjunto de dois anti-inflamatórios/antiagregantes aumenta o risco de sangramento gastrointestinal.'),
  ('a2000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000002', 'c1000001-0000-0000-0000-000000000001', 'grave', 'Ibuprofeno potencializa o efeito anticoagulante da varfarina e aumenta risco de sangramento — encaminhar ao farmacêutico/médico.'),
  ('a2000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000002', 'c1000000-0000-0000-0000-000000000003', 'moderada', 'Associação de dois anti-inflamatórios não esteroidais aumenta risco de efeitos adversos gastrointestinais e renais.'),
  ('a2000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000000001', 'c1000001-0000-0000-0000-000000000002', 'grave', 'Paracetamol com consumo de álcool aumenta significativamente o risco de hepatotoxicidade.'),
  ('a2000000-0000-0000-0000-000000000005', 'c1000000-0000-0000-0000-000000000002', 'c1000001-0000-0000-0000-000000000005', 'grave', 'Pseudoefedrina com inibidores da MAO pode causar crise hipertensiva grave — contraindicado.'),
  ('a2000000-0000-0000-0000-000000000006', 'c1000000-0000-0000-0000-000000000002', 'c1000001-0000-0000-0000-000000000006', 'moderada', 'Pseudoefedrina pode reduzir o efeito de anti-hipertensivos e elevar a pressão arterial.'),
  ('a2000000-0000-0000-0000-000000000007', 'c1000000-0000-0000-0000-000000000019', 'c1000001-0000-0000-0000-000000000001', 'grave', 'Fluconazol potencializa o efeito da varfarina, aumentando risco de sangramento — encaminhar ao farmacêutico/médico.'),
  ('a2000000-0000-0000-0000-000000000008', 'c1000000-0000-0000-0000-000000000001', 'c1000001-0000-0000-0000-000000000002', 'moderada', 'Dexclorfeniramina com álcool potencializa sedação e prejudica reflexos.'),
  ('a2000000-0000-0000-0000-000000000009', 'c1000000-0000-0000-0000-000000000008', 'c1000001-0000-0000-0000-000000000007', 'moderada', 'Metoclopramida associada a antipsicóticos aumenta risco de sintomas extrapiramidais.'),
  ('a2000000-0000-0000-0000-000000000010', 'c1000000-0000-0000-0000-000000000010', 'c1000001-0000-0000-0000-000000000003', 'leve', 'Cálcio pode reduzir a absorção de ferro quando administrados juntos — espaçar as doses em pelo menos 2 horas.'),
  ('a2000000-0000-0000-0000-000000000011', 'c0000000-0000-0000-0000-000000000006', 'c1000001-0000-0000-0000-000000000004', 'moderada', 'Omeprazol pode reduzir a eficácia antiplaquetária do clopidogrel.'),
  ('a2000000-0000-0000-0000-000000000012', 'c1000000-0000-0000-0000-000000000007', 'c1000000-0000-0000-0000-000000000019', 'grave', 'Domperidona associada a antifúngicos azólicos (classe do fluconazol) aumenta risco de arritmia cardíaca (prolongamento de QT).'),
  ('a2000000-0000-0000-0000-000000000013', 'c1000000-0000-0000-0000-000000000013', 'c1000001-0000-0000-0000-000000000003', 'leve', 'Vitamina C aumenta a absorção de ferro — geralmente benéfico, mas pode exigir ajuste de dose em suplementação combinada.'),
  ('a2000000-0000-0000-0000-000000000014', 'c1000000-0000-0000-0000-000000000004', 'c1000001-0000-0000-0000-000000000001', 'grave', 'Naproxeno potencializa o efeito anticoagulante da varfarina e aumenta risco de sangramento — encaminhar ao farmacêutico/médico.'),
  ('a2000000-0000-0000-0000-000000000015', 'c1000000-0000-0000-0000-000000000010', 'c1000000-0000-0000-0000-000000000016', 'leve', 'Cálcio pode reduzir a absorção de zinco quando administrados juntos — espaçar as doses em pelo menos 2 horas.')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Restrições de uso (20). Só usa os 8 valores existentes de tipo_restricao_enum
-- (gestante/lactante/pediatrico/idoso/insuficiencia_renal/insuficiencia_
-- hepatica/hipertenso/diabetico) — pedidos que não mapeiam pra nenhum desses
-- (úlcera péptica, cardiopatia, Parkinson, alcoolismo, "operador de máquina")
-- ficaram de fora, ver nota 5 no topo do arquivo.
-- ---------------------------------------------------------------------------
INSERT INTO restricoes_uso_principio_ativo (id, principio_ativo_id, tipo_restricao, nivel, descricao) VALUES
  ('a3000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'gestante', 'contraindicado', 'Ibuprofeno contraindicado no 3º trimestre de gestação (risco de fechamento precoce do canal arterial).'),
  ('a3000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000002', 'pediatrico', 'cautela', 'Uso em menores de 12 anos requer orientação — não recomendar sem checar peso/idade.'),
  ('a3000000-0000-0000-0000-000000000003', 'c1000000-0000-0000-0000-000000000003', 'pediatrico', 'contraindicado', 'Nimesulida contraindicada em menores de 12 anos.'),
  ('a3000000-0000-0000-0000-000000000004', 'c1000000-0000-0000-0000-000000000003', 'gestante', 'contraindicado', 'Nimesulida contraindicada durante toda a gestação.'),
  ('a3000000-0000-0000-0000-000000000005', 'c1000000-0000-0000-0000-000000000003', 'insuficiencia_hepatica', 'contraindicado', 'Nimesulida contraindicada em histórico de hepatite ou hepatopatia (risco de hepatotoxicidade).'),
  ('a3000000-0000-0000-0000-000000000006', 'c1000000-0000-0000-0000-000000000005', 'pediatrico', 'contraindicado', 'AAS contraindicado em menores de 12 anos com quadro viral (risco de Síndrome de Reye).'),
  ('a3000000-0000-0000-0000-000000000007', 'c1000000-0000-0000-0000-000000000005', 'gestante', 'contraindicado', 'AAS contraindicado no 3º trimestre de gestação.'),
  ('a3000000-0000-0000-0000-000000000008', 'c1000000-0000-0000-0000-000000000002', 'hipertenso', 'cautela', 'Pseudoefedrina pode elevar a pressão arterial — cautela em hipertensos.'),
  ('a3000000-0000-0000-0000-000000000009', 'c1000000-0000-0000-0000-000000000002', 'gestante', 'cautela', 'Pseudoefedrina requer avaliação médica durante a gestação.'),
  ('a3000000-0000-0000-0000-000000000010', 'c1000000-0000-0000-0000-000000000001', 'lactante', 'cautela', 'Dexclorfeniramina pode passar pelo leite materno e causar sonolência no lactente.'),
  ('a3000000-0000-0000-0000-000000000011', 'c1000000-0000-0000-0000-000000000001', 'pediatrico', 'contraindicado', 'Dexclorfeniramina contraindicada em menores de 2 anos.'),
  ('a3000000-0000-0000-0000-000000000012', 'c1000000-0000-0000-0000-000000000019', 'gestante', 'contraindicado', 'Fluconazol classificado como categoria D (FDA) — risco confirmado ao feto, contraindicado na gestação.'),
  ('a3000000-0000-0000-0000-000000000013', 'c1000000-0000-0000-0000-000000000008', 'pediatrico', 'contraindicado', 'Metoclopramida contraindicada em menores de 1 ano (risco de efeitos extrapiramidais).'),
  ('a3000000-0000-0000-0000-000000000014', 'c1000000-0000-0000-0000-000000000017', 'gestante', 'contraindicado', 'Melatonina sem estudos de segurança suficientes na gestação — contraindicada.'),
  ('a3000000-0000-0000-0000-000000000015', 'c1000000-0000-0000-0000-000000000017', 'pediatrico', 'cautela', 'Melatonina em menores de 18 anos requer orientação — não recomendar sem avaliação.'),
  ('a3000000-0000-0000-0000-000000000016', 'c0000000-0000-0000-0000-000000000001', 'insuficiencia_hepatica', 'cautela', 'Paracetamol em dose alta requer cautela em hepatopatas — risco de hepatotoxicidade aumentado.'),
  ('a3000000-0000-0000-0000-000000000017', 'c1000000-0000-0000-0000-000000000004', 'gestante', 'contraindicado', 'Naproxeno contraindicado no 3º trimestre de gestação (mesma classe do ibuprofeno).'),
  ('a3000000-0000-0000-0000-000000000018', 'c1000000-0000-0000-0000-000000000004', 'insuficiencia_renal', 'cautela', 'Anti-inflamatórios não esteroidais podem agravar disfunção renal — cautela em insuficiência renal.'),
  ('a3000000-0000-0000-0000-000000000019', 'c0000000-0000-0000-0000-000000000006', 'idoso', 'cautela', 'Uso prolongado de inibidor de bomba de prótons em idosos associado a maior risco de fratura óssea.'),
  ('a3000000-0000-0000-0000-000000000020', 'c1000000-0000-0000-0000-000000000010', 'insuficiencia_renal', 'cautela', 'Suplementação de cálcio requer cautela em insuficiência renal (risco de hipercalcemia).')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Lotes (1 por produto novo) — validade sempre relativa a CURRENT_DATE.
-- ---------------------------------------------------------------------------
INSERT INTO lotes (id, produto_id, numero_lote, data_fabricacao, data_validade, quantidade_recebida, custo_unitario, status)
SELECT
  ('e1000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  ('d1000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  'SEED2-' || lpad(n::text, 3, '0'),
  CURRENT_DATE - INTERVAL '30 days',
  CURRENT_DATE + INTERVAL '1 year',
  100,
  10.00,
  'disponivel'
FROM generate_series(1, 86) AS n
JOIN produtos p ON p.id = ('d1000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Estoque (1 registro por lote, na filial existente, quantidade_atual=100)
-- ---------------------------------------------------------------------------
INSERT INTO estoque (id, filial_id, lote_id, quantidade_atual)
SELECT
  ('f1000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  '6af7109e-c8ed-4b17-9f0a-3b7346e2c1f2',
  ('e1000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
  100
FROM generate_series(1, 86) AS n
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Conferência
-- ---------------------------------------------------------------------------
SELECT
  (SELECT count(*) FROM fabricantes) AS total_fabricantes,
  (SELECT count(*) FROM principios_ativos) AS total_principios,
  (SELECT count(*) FROM produtos WHERE tarja = 'isento') AS total_produtos_isento,
  (SELECT count(*) FROM interacoes_medicamentosas) AS total_interacoes,
  (SELECT count(*) FROM restricoes_uso_principio_ativo) AS total_restricoes,
  (SELECT count(*) FROM lotes) AS total_lotes,
  (SELECT count(*) FROM estoque WHERE quantidade_atual = 100) AS total_estoque;
