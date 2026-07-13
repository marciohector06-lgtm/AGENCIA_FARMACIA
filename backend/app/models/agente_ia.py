import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TipoAgenteEnum, pg_enum


class AgenteIA(Base):
    __tablename__ = "agentes_ia"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[TipoAgenteEnum] = mapped_column(pg_enum(TipoAgenteEnum, "tipo_agente_enum"), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    descricao: Mapped[str | None]
    db_role_name: Mapped[str] = mapped_column(String(63), nullable=False)
    modelo_llm: Mapped[str] = mapped_column(String(80), nullable=False, default="gemini-1.5-pro")
    versao: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
