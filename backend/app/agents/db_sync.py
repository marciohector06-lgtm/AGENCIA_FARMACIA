from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agents.config import AgentRole, get_agent_settings


@lru_cache
def _engine_for(role: AgentRole):
    settings = get_agent_settings()
    connect_args: dict[str, object] = (
        {"sslmode": "require"}
        if settings.db_ssl_require and settings.database_url_for(role).startswith("postgresql+psycopg2://")
        else {}
    )
    return create_engine(
        settings.database_url_for(role),
        pool_pre_ping=True,
        connect_args=connect_args,
        future=True,
        # FASE 1 (SEC-12): antes disso o pool ficava no default implícito do
        # SQLAlchemy (5 + 10 de overflow) sem ninguém ter decidido isso de
        # propósito. Cada agent_session() só seguraconexão pelo tempo de um
        # bloco `with` (não a requisição HTTP inteira), então 10+10 dá folga
        # confortável mesmo com vários chats concorrentes de IPs diferentes
        # batendo no limite de 10/min do SEC-02 ao mesmo tempo — sem abrir
        # pool descontroladamente grande, que só trocaria "conexão esgotada"
        # por "Postgres sobrecarregado".
        pool_size=10,
        max_overflow=10,
    )


@lru_cache
def _session_factory_for(role: AgentRole) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine_for(role), expire_on_commit=False)


@contextmanager
def agent_session(role: AgentRole) -> Iterator[Session]:
    """Abre uma sessão síncrona autenticada como a role Postgres daquele agente.

    Nunca usa a role app_backend: cada agente só enxerga/edita o que a FASE 1
    (RLS + GRANT) permitiu para ele, mesmo que o código Python tente mais.
    """
    session_factory = _session_factory_for(role)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
