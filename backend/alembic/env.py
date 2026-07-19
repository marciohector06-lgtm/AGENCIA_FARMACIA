import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Usado por autogenerate em migrations futuras (a partir da baseline 0001,
# que é gerada a mão a partir das 28 SQL migrations históricas — não por
# comparação com este metadata).
target_metadata = Base.metadata


def _sync_db_url() -> str:
    """DATABASE_URL da app é async (postgresql+asyncpg); Alembic roda
    migrations com um driver síncrono. TEST_DATABASE_URL (usado pela suíte
    de testes e pelo CI) tem prioridade sobre DATABASE_URL quando setada.

    IMPORTANTE: nunca passe essa URL por config.set_main_option()/
    engine_from_config() — o Alembic lê alembic.ini com configparser por
    baixo dos panos, e configparser trata "%" como caractere de
    interpolação. Uma senha do Supabase com caracteres especiais
    url-encoded (ex.: "@@" -> "%40%40") quebra ao ser lida de volta do
    objeto `config`. create_engine() direto com a string, sem tocar em
    `config`, evita esse parsing por completo.
    """
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL (ou TEST_DATABASE_URL) precisa estar setada no "
            "ambiente para rodar migrations do Alembic."
        )
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://").replace(
        "postgresql://", "postgresql+psycopg2://"
    )


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=_sync_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(_sync_db_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Migration 0005/0006 (Agente Tributário): Postgres não deixa usar,
            # na MESMA transação, um valor de enum que acabou de ser
            # adicionado via ALTER TYPE ... ADD VALUE. Sem isto, um único
            # `alembic upgrade head` roda TODAS as migrations pendentes numa
            # única transação (um só context.begin_transaction() por
            # invocação) — 0006 usar 'tributario' (adicionado na 0005) quebra
            # com "unsafe use of new value" mesmo estando em arquivos
            # separados. Com transaction_per_migration=True, cada migration
            # commita antes da próxima começar, igual rodar cada uma como um
            # `alembic upgrade` isolado.
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
