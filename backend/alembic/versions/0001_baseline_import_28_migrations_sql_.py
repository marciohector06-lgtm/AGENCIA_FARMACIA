"""baseline import 28 migrations sql historicas

Revision ID: 0001
Revises:
Create Date: 2026-07-14 09:30:28.537216

Esta revision representa o schema construído pelas 28 migrations SQL em
database/migrations/ (0001_extensions.sql .. 0028_sessoes_chat_historico.sql),
escritas e aplicadas manualmente entre a FASE 0 e a FASE 4, antes da adoção
do Alembic (FASE 6 / QA-01). Esses 28 arquivos continuam em
database/migrations/ como referência histórica — não editar, não remover.

- Banco já existente (produção/Supabase, onde as 28 SQL já rodaram
  manualmente): rode `alembic stamp head` — NUNCA `alembic upgrade head`,
  que tentaria recriar objetos já existentes.
- Banco novo (Postgres de teste local, CI): `alembic upgrade head` executa o
  conteúdo literal dos 28 arquivos, em ordem, construindo o schema do zero.

Toda migration a partir daqui (inclusive a de pseudonimização da LGPD,
FASE 5) é gerada pelo Alembic normalmente.
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# backend/alembic/versions/ -> parents[3] é a raiz do repositório.
_SQL_DIR = Path(__file__).resolve().parents[3] / "database" / "migrations"

_SQL_FILES = [
    "0001_extensions.sql",
    "0002_enums.sql",
    "0003_tabelas_apoio.sql",
    "0004_tabelas_clinicas.sql",
    "0005_tabelas_produtos.sql",
    "0006_tabelas_estoque.sql",
    "0007_tabelas_vendas.sql",
    "0008_tabela_auditoria.sql",
    "0009_indexes.sql",
    "0010_views.sql",
    "0011_roles_grants.sql",
    "0012_rls_policies.sql",
    "0013_triggers_functions.sql",
    "0014_rls_apoio.sql",
    "0015_seed_agentes.sql",
    "0016_grant_margem_resultante.sql",
    "0017_grant_select_proprio_log.sql",
    "0018_grant_select_vendas_atendente.sql",
    "0019_fronteira_erp.sql",
    "0020_operadores_auth.sql",
    "0021_security_invoker_search_path.sql",
    "0022_fefo_correto.sql",
    "0023_remove_rag_schema_morto.sql",
    "0024_margem_numeric_7_2.sql",
    "0025_proposta_desconto_unica_por_lote.sql",
    "0026_atendente_le_precificacao.sql",
    "0027_auditoria_modelo_e_metricas.sql",
    "0028_sessoes_chat_historico.sql",
]


def upgrade() -> None:
    # Executa via cursor DBAPI puro (não conn.exec_driver_sql): várias das 28
    # SQL migrations têm literais com "%" (ex.: url-encoding em comentários),
    # e o binding de parâmetros do SQLAlchemy/psycopg2 interpreta "%" como
    # marcador de placeholder mesmo sem parâmetros de fato.
    dbapi_conn = op.get_bind().connection.dbapi_connection
    if dbapi_conn is None:
        raise RuntimeError("Sem conexão DBAPI ativa para aplicar a baseline.")
    for filename in _SQL_FILES:
        sql_text = (_SQL_DIR / filename).read_text(encoding="utf-8")
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute(sql_text)
        finally:
            cursor.close()


def downgrade() -> None:
    raise RuntimeError(
        "A baseline 0001 representa 28 migrations SQL historicas aplicadas "
        "manualmente em producao (roles, RLS, triggers, schema completo). "
        "Nao existe downgrade seguro para ela: desfaze-la destruiria o "
        "banco inteiro. Para descartar um Postgres de teste/CI, derrube o "
        "container/banco diretamente em vez de rodar alembic downgrade "
        "alem desta revision."
    )
