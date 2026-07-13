import os
import uuid

# Garante que a Settings() consiga ser instanciada mesmo sem um .env real
# (ex.: em CI). Testes que dependem de banco de verdade usam TEST_DATABASE_URL
# via dependency override abaixo e são pulados quando ela não está definida.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder:placeholder@localhost:5432/placeholder")

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.db import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or None


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = None
    if TEST_DATABASE_URL:
        # Mesmo motivo do app/core/db.py — necessário quando TEST_DATABASE_URL
        # aponta para o pooler do Supabase em modo transaction.
        engine = create_async_engine(
            TEST_DATABASE_URL,
            poolclass=NullPool,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
            },
        )
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    if engine is not None:
        await engine.dispose()
