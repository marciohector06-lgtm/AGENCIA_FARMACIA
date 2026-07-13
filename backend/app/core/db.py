import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# Supabase exige TLS em conexões diretas ao Postgres. Desative apenas para um
# Postgres local de desenvolvimento via DB_SSL_REQUIRE=false no .env.
_connect_args: dict[str, object] = {"ssl": "require"} if settings.db_ssl_require else {}
# O backend se conecta via Connection Pooler do Supabase em modo "Transaction"
# (porta 6543/PgBouncer-Supavisor). Nesse modo, prepared statements nomeados de
# forma previsível colidem entre conexões físicas reusadas por clientes
# diferentes. Fix oficial do SQLAlchemy (docs do dialect asyncpg): NullPool
# (deixa o pooling a cargo do Supabase, não duplica pool no lado da app) +
# nome de prepared statement único por chamada via uuid4.
# https://github.com/sqlalchemy/sqlalchemy/issues/6467
_connect_args["statement_cache_size"] = 0
_connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4()}__"

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    poolclass=NullPool,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
