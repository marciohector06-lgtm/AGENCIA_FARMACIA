-- FASE 1: Funções e triggers de manutenção estrutural.

CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_upd_filiais BEFORE UPDATE ON filiais
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_upd_fabricantes BEFORE UPDATE ON fabricantes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_upd_principios_ativos BEFORE UPDATE ON principios_ativos
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_upd_produtos BEFORE UPDATE ON produtos
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_upd_clientes BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
CREATE TRIGGER trg_upd_estoque BEFORE UPDATE ON estoque
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- Marca lotes vencidos automaticamente. Agendada via pg_cron para rodar
-- diariamente; SECURITY DEFINER porque nenhuma role de agente tem UPDATE
-- irrestrito em lotes.status fora do próprio fluxo do Agente Gerente de Estoque.
CREATE OR REPLACE FUNCTION fn_atualizar_lotes_vencidos() RETURNS void AS $$
BEGIN
    UPDATE lotes SET status = 'vencido'
    WHERE data_validade < CURRENT_DATE
      AND status NOT IN ('vencido', 'devolvido');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Requer a extensão pg_cron habilitada (0001) e permissão de schedule no
-- projeto Supabase (Dashboard > Database > Extensions/Cron).
SELECT cron.schedule(
    'atualizar-lotes-vencidos',
    '0 3 * * *',
    $$SELECT fn_atualizar_lotes_vencidos();$$
);
