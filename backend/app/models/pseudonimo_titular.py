import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PseudonimoTitular(Base):
    """LGPD-04: única ligação entre um pseudonimo_id (o que logs_auditoria e
    sessoes_chat_mensagens gravam) e um cliente_id de verdade. Só app_backend
    tem acesso — nenhuma role de agente (migration 0002_lgpd_04...).

    Revogar (revogado_em preenchido + cliente_id nulo) elimina o vínculo com
    o titular sem tocar nas linhas de auditoria que referenciam este
    pseudonimo_id: elas continuam existindo, só ficam desvinculadas.
    """

    __tablename__ = "pseudonimos_titular"

    pseudonimo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="SET NULL"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
