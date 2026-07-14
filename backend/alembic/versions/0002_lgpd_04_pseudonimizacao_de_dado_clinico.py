"""LGPD-04 pseudonimizacao de dado clinico

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-14 14:10:07.813040

Dado clínico (sintoma relatado, medicamentos_em_uso, texto de conversa) passa
a ser gravado em logs_auditoria/sessoes_chat_mensagens ligado a um
pseudonimo_id, nunca a cliente_id direto. pseudonimos_titular guarda a única
ligação pseudonimo_id -> cliente_id, revogável (right to erasure, LGPD art.
18) sem tocar em nenhuma linha de auditoria — que continua append-only,
provando a decisão da IA sem precisar provar quem era o titular.

Atômico com a correção do LGPD-02: agente_orquestrador tinha, por um GRANT
genérico demais (0011: "GRANT SELECT ON ALL TABLES IN SCHEMA public"),
acesso de leitura a clientes.cpf sem nenhuma tool/caso de uso que precisasse
disso. Revogado aqui — ou a pseudonimização entra completa com isso corrigido,
ou nada entra.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pseudonimos_titular",
        sa.Column("pseudonimo_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cliente_id", UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
    )
    # No máximo um pseudônimo ATIVO por cliente por vez — pseudonimo_id_for_cliente
    # (app/agents/pseudonimos.py) faz get-or-create sobre essa garantia; depois de
    # revogado, uma nova sessão do mesmo cliente cria um pseudônimo novo.
    op.execute(
        "CREATE UNIQUE INDEX idx_pseudonimos_titular_cliente_ativo "
        "ON pseudonimos_titular (cliente_id) WHERE revogado_em IS NULL"
    )

    op.add_column(
        "logs_auditoria",
        sa.Column("pseudonimo_id", UUID(as_uuid=True), sa.ForeignKey("pseudonimos_titular.pseudonimo_id"), nullable=True),
    )
    op.add_column(
        "sessoes_chat_mensagens",
        sa.Column("pseudonimo_id", UUID(as_uuid=True), sa.ForeignKey("pseudonimos_titular.pseudonimo_id"), nullable=True),
    )
    op.execute("CREATE INDEX idx_logs_auditoria_pseudonimo ON logs_auditoria (pseudonimo_id)")
    op.execute("CREATE INDEX idx_sessoes_chat_mensagens_pseudonimo ON sessoes_chat_mensagens (pseudonimo_id)")

    # RLS: só app_backend. Nenhuma role de agente recebe GRANT nenhum aqui —
    # REVOKE explícito abaixo é defesa em profundidade/documentação (mesmo
    # padrão de "baseline: nenhuma role de agente começa com privilégio" de
    # 0011), já que tabela nova não herda GRANTs antigos automaticamente.
    op.execute("ALTER TABLE pseudonimos_titular ENABLE ROW LEVEL SECURITY")
    op.execute("GRANT SELECT, INSERT, UPDATE ON pseudonimos_titular TO app_backend")
    op.execute(
        "CREATE POLICY all_backend ON pseudonimos_titular FOR ALL TO app_backend USING (true) WITH CHECK (true)"
    )
    op.execute(
        "REVOKE ALL ON pseudonimos_titular FROM "
        "agente_atendente, agente_estoque, agente_financeiro, agente_orquestrador"
    )

    # LGPD-02: agente_orquestrador não tem nenhum caso de uso que leia
    # clientes (grep em app/agents/, app/integrations/ não mostra nenhuma
    # tool/role orquestrador consultando essa tabela) — o GRANT genérico de
    # 0011 e a policy de 0014 davam acesso a CPF sem necessidade nenhuma.
    op.execute("DROP POLICY IF EXISTS sel_orquestrador ON clientes")
    op.execute("REVOKE SELECT ON clientes FROM agente_orquestrador")


def downgrade() -> None:
    op.execute("GRANT SELECT ON clientes TO agente_orquestrador")
    op.execute("CREATE POLICY sel_orquestrador ON clientes FOR SELECT TO agente_orquestrador USING (true)")

    op.execute("DROP INDEX IF EXISTS idx_sessoes_chat_mensagens_pseudonimo")
    op.execute("DROP INDEX IF EXISTS idx_logs_auditoria_pseudonimo")
    op.drop_column("sessoes_chat_mensagens", "pseudonimo_id")
    op.drop_column("logs_auditoria", "pseudonimo_id")

    op.execute("DROP POLICY IF EXISTS all_backend ON pseudonimos_titular")
    op.drop_table("pseudonimos_titular")
