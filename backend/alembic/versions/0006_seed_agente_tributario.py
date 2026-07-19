"""agente tributario: seed em agentes_ia

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-19 10:05:00.000000

Registra o Agente Tributário em agentes_ia — é a essa linha que
logs_auditoria.agente_id aponta (via app/agents/registry.py::agente_id_for)
sempre que o agente registra uma decisão. Mesmo padrão de
database/migrations/0015_seed_agentes.sql.

Separada da 0005 de propósito: o valor 'tributario' do tipo_agente_enum foi
adicionado na 0005, e Postgres não deixa usar um valor de enum recém-criado
na mesma transação em que ele foi adicionado.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO agentes_ia (tipo, nome, descricao, db_role_name, modelo_llm, versao)
        VALUES (
            'tributario',
            'Especialista Tributário',
            'Processa NF-e recebidas por email, identifica produtos no cadastro e prepara '
            'entrada de estoque para confirmação humana (Bloco 1 — sem cálculo tributário).',
            'agente_tributario',
            'gemini-2.5-pro',
            '1.0.0'
        )
        ON CONFLICT (tipo, nome) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM agentes_ia WHERE tipo = 'tributario' AND nome = 'Especialista Tributário'")
