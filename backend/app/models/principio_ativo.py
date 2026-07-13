import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class PrincipioAtivo(TimestampMixin, Base):
    __tablename__ = "principios_ativos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    nome_dcb: Mapped[str | None] = mapped_column(String(150))
    classe_terapeutica: Mapped[str] = mapped_column(String(120), nullable=False)
    mecanismo_acao: Mapped[str | None] = mapped_column(Text)
    contraindicacoes_gerais: Mapped[str | None] = mapped_column(Text)
