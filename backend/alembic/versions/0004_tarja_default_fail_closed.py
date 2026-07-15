"""tarja default fail-closed (vermelha em vez de isento)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-15 09:00:00.000000

QA (auditoria do cadastro manual de produtos): produtos.tarja tinha
DEFAULT 'isento' desde a migration 0005 — o valor MENOS restritivo. Isso
contradiz a regra já estabelecida em app/integrations/sync.py::_mapear_tarja
("se não dá pra provar que é MIP, vira 'vermelha'"): lá, tarja ausente/não
mapeável falha fechado para o mais restritivo; no cadastro manual, tarja
ausente falhava aberto para o menos restritivo. Nenhum código do projeto
depende deste default (sync sempre define tarja explicitamente antes do
flush; todo INSERT bruto em tests/ especifica a coluna) — confirmado antes
desta migration ser escrita.

ProdutoCreate (schemas/produto.py) passa a exigir tarja explicitamente
(sem default no Pydantic), então este DEFAULT do banco nunca deveria ser
acionado por uma requisição via API — ele é só a última rede de segurança
(um INSERT manual/futuro que esqueça a coluna) e agora aponta pro lado
seguro, coerente com o resto do sistema.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "produtos",
        "tarja",
        server_default=sa.text("'vermelha'::tarja_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "produtos",
        "tarja",
        server_default=sa.text("'isento'::tarja_enum"),
    )
