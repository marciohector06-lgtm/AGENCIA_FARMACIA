import os
import uuid

# Garante que a Settings() consiga ser instanciada mesmo sem um .env real
# (ex.: em CI). Testes que dependem de banco de verdade usam TEST_DATABASE_URL
# via dependency override abaixo e são pulados quando ela não está definida.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder:placeholder@localhost:5432/placeholder")
# FASE 1 (SEC-01): Settings() exige um jwt_secret_key real — nunca um default
# hardcoded em produção, mas testes precisam de ALGUM valor pra instanciar.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-nunca-use-isto-em-producao")

# IMPORTANTE: AgentSettings lê backend/.env (pydantic-settings, env_file=".env")
# quando a variável de ambiente do processo não está setada — se alguém tiver
# uma GEMINI_API_KEY real nesse .env local, os testes fariam chamadas de
# verdade à API do Gemini sem querer (isso aconteceu uma vez ao escrever os
# testes de rate limit da FASE 1). Sobrescrever (não só setdefault) força o
# caminho rápido de RuntimeError em build_llm(), sem nenhuma chamada de rede.
os.environ["GEMINI_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.auth import OperadorAutenticado, get_current_operador
from app.core.db import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or None


def _override_get_db():
    if not TEST_DATABASE_URL:
        return None
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

    return engine, override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente "autenticado por default": a maioria dos testes não está
    testando SEC-01 em si, então sobrescrevemos get_current_operador pra não
    precisar carregar um JWT real em cada chamada. Quem precisa testar
    autenticação de verdade usa o fixture `raw_client` abaixo."""
    result = _override_get_db()
    engine = None
    if result is not None:
        engine, override_get_db = result
        app.dependency_overrides[get_db] = override_get_db

    app.dependency_overrides[get_current_operador] = lambda: OperadorAutenticado(
        operador_id="00000000-0000-0000-0000-000000000000", email="teste@fixture.local"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    if engine is not None:
        await engine.dispose()


@pytest_asyncio.fixture
async def raw_client() -> AsyncGenerator[AsyncClient, None]:
    """Sem override de autenticação — para os testes que exercitam SEC-01 de
    verdade (token ausente, inválido, expirado, válido)."""
    result = _override_get_db()
    engine = None
    if result is not None:
        engine, override_get_db = result
        app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    if engine is not None:
        await engine.dispose()
