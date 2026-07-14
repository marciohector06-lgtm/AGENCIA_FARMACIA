"""LGPD-03 consentimento do titular

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-14 14:11:08.513960

consentimento_dado/consentimento_lgpd_em em clientes: POST
/clientes/{id}/consentimento é o único jeito de setar isso (nunca o PATCH
genérico de clientes) — mantém um carimbo de quando o aviso de IA foi aceito.
Sem consentimento registrado (quando cliente_id é informado), /chat/atendimento
recusa com 403.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clientes", sa.Column("consentimento_dado", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        "clientes", sa.Column("consentimento_lgpd_em", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("clientes", "consentimento_lgpd_em")
    op.drop_column("clientes", "consentimento_dado")
