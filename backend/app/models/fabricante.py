import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Fabricante(TimestampMixin, Base):
    __tablename__ = "fabricantes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)
    registro_anvisa: Mapped[str | None] = mapped_column(String(30))
    pais_origem: Mapped[str] = mapped_column(String(60), nullable=False, default="Brasil")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
