import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import OrigemErpMixin, TimestampMixin


class Filial(OrigemErpMixin, TimestampMixin, Base):
    __tablename__ = "filiais"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)
    endereco: Mapped[str | None] = mapped_column(String(255))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
