from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OrigemErpMixin:
    """FASE 0 (migration 0019): de quem é a linha. 'manual' = nosso Postgres é a
    fonte da verdade (farmácia sem ERP); qualquer outro valor = nome do ERP
    (ex.: 'mock', 'linx') e a linha é somente leitura pela API — o ERP manda.
    """

    id_externo: Mapped[str | None] = mapped_column(String(64))
    origem: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    sincronizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def editavel_via_api(self) -> bool:
        return self.origem == "manual"
