-- FASE 1 (SEC-03 + SEC-04): duas linhas de risco clínico alto.
--
-- SEC-03: views no Postgres rodam com o privilégio do DONO por padrão, não
-- do chamador — mesmo com a RLS de 0012 filtrando produtos.tarja='isento'
-- pra agente_atendente, vw_estoque_atual (JOIN produtos) expunha p.tarja e
-- TODOS os produtos, tarja preta incluída, porque a view em si não estava
-- sujeita à RLS de quem a consulta. security_invoker=on faz a view herdar o
-- privilégio (e a RLS) de quem chama, não de quem criou.
--
-- SEC-04: funções SECURITY DEFINER sem search_path fixo são sequestráveis —
-- alguém com permissão de criar objetos no schema public poderia criar uma
-- função/tabela com o mesmo nome de algo que a função referencia (ex.: um
-- "estoque" ou "agentes_ia" forjado) num schema que apareça antes de public
-- na search_path da sessão, e a função DEFINER executaria isso com
-- privilégio elevado. Fixar search_path elimina essa ambiguidade.
ALTER VIEW vw_estoque_atual SET (security_invoker = on);
ALTER VIEW vw_produtos_substituiveis SET (security_invoker = on);
ALTER VIEW vw_giro_estoque_90d SET (security_invoker = on);

ALTER FUNCTION fn_atualizar_lotes_vencidos() SET search_path = public, pg_temp;
ALTER FUNCTION current_agente_id() SET search_path = public, pg_temp;

-- Efeito colateral necessário do security_invoker=on: a partir de agora
-- vw_estoque_atual roda com o privilégio de QUEM CHAMA, então esse chamador
-- precisa ter GRANT nas colunas que a definição da view referencia (mesmo
-- que a query externa não as liste no SELECT) — não só nas que costumava
-- usar. agente_atendente ganhou SELECT em filiais (id, origem, id_externo)
-- na migration 0019 pro fluxo F0-06; a view também referencia filiais.nome
-- (f.nome AS filial_nome), então precisa dessa coluna também.
GRANT SELECT (nome) ON filiais TO agente_atendente;
