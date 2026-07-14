import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Cliente(TimestampMixin, Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    # LGPD-03: só setado via POST /clientes/{id}/consentimento — nunca pelo
    # PATCH genérico. consentimento_lgpd_em é o carimbo de quando o aviso de
    # atendimento por IA foi aceito.
    consentimento_dado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consentimento_lgpd_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
