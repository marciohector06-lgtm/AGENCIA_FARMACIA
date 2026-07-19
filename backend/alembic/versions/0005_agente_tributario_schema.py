"""agente tributario: schema de notas fiscais de entrada (Bloco 1)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19 10:00:00.000000

Quinto agente do sistema: o Agente Tributário. Bloco 1 (este) cobre só a
leitura de NF-e por email e a preparação da entrada de estoque — a
confirmação em si (que de fato escreve em lotes/estoque/movimentacoes_estoque)
é feita exclusivamente por app_backend, num endpoint separado, nunca pelo
agente. O Bloco 2 (cálculo tributário) fica para uma fase futura.

Duas tabelas novas (notas_fiscais_entrada, notas_fiscais_entrada_itens), dois
ENUMs novos (mesma convenção do resto do schema — nada de VARCHAR solto pra
status), um valor novo em dois ENUMs existentes, e a role de banco
agente_tributario com GRANTs mínimos (mesmo padrão de
database/migrations/0011_roles_grants.sql, agora via Alembic).

IMPORTANTE: esta migration NÃO faz o INSERT em agentes_ia com
tipo='tributario' — isso fica na migration 0006, separada de propósito.
Postgres não permite usar, na MESMA transação, um valor de enum que acabou
de ser adicionado via ALTER TYPE ... ADD VALUE (mesmo em versões que
permitem o ADD VALUE dentro de uma transação). Como o env.py deste projeto
roda cada migration dentro de uma transação, misturar o ADD VALUE
'tributario' com um INSERT que usa esse valor na mesma migration quebraria
em runtime.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # ENUMs novos — mesma convenção do resto do schema (nunca VARCHAR solto
    # pra um campo de status).
    # =========================================================================
    status_nfe_entrada_enum = sa.Enum(
        "aguardando_confirmacao", "confirmada", "cancelada", name="status_nfe_entrada_enum"
    )
    status_item_nfe_enum = sa.Enum(
        "identificado", "nao_encontrado", "cadastrado_automaticamente", name="status_item_nfe_enum"
    )
    status_nfe_entrada_enum.create(op.get_bind())
    status_item_nfe_enum.create(op.get_bind())
    # create_type=False DEPOIS de criar o tipo à mão: sem isso, create_table()
    # mais abaixo tenta criar o mesmo tipo de novo sozinho (SQLAlchemy cria
    # automaticamente o ENUM de uma coluna ao criar a tabela) e quebra com
    # "type already exists". Precisa ser o ENUM dialect-specific do
    # postgresql (não o sa.Enum genérico, que ACEITA o kwarg create_type sem
    # erro mas silenciosamente IGNORA — sa.Enum genérico não expõe nem lê
    # esse atributo; só sqlalchemy.dialects.postgresql.ENUM respeita de
    # verdade) — mesmo tipo usado por pg_enum() em app/models/enums.py.
    status_nfe_entrada_enum_col = PGEnum(
        "aguardando_confirmacao", "confirmada", "cancelada", name="status_nfe_entrada_enum", create_type=False
    )
    status_item_nfe_enum_col = PGEnum(
        "identificado",
        "nao_encontrado",
        "cadastrado_automaticamente",
        name="status_item_nfe_enum",
        create_type=False,
    )

    # Valores novos em ENUMs já existentes (não usados nesta migration —
    # 'tributario' só é usado na 0006, 'entrada_nfe' só é usado em runtime
    # pelo endpoint de confirmação, nunca numa migration).
    op.execute("ALTER TYPE tipo_movimentacao_enum ADD VALUE IF NOT EXISTS 'entrada_nfe'")
    op.execute("ALTER TYPE tipo_agente_enum ADD VALUE IF NOT EXISTS 'tributario'")
    op.execute("ALTER TYPE tipo_decisao_enum ADD VALUE IF NOT EXISTS 'entrada_nfe_processada'")

    # =========================================================================
    # produtos.ncm: não existia no schema. IdentificarProdutosTool precisa
    # comparar o NCM do item da NF-e contra o cadastro — sem essa coluna a
    # busca por NCM (a mais confiável das duas, vs. nome aproximado) seria
    # sempre um no-op. Nullable: cadastro existente não tem esse dado
    # retroativamente: text() na definição vale como default apenas no
    # sentido "nunca obrigatório", nunca API force-preenche às cegas.
    # =========================================================================
    op.add_column("produtos", sa.Column("ncm", sa.String(10), nullable=True))
    op.create_index("idx_produtos_ncm", "produtos", ["ncm"], postgresql_where=sa.text("ncm IS NOT NULL"))

    # =========================================================================
    # Tabelas
    # =========================================================================
    op.create_table(
        "notas_fiscais_entrada",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filial_id", UUID(as_uuid=True), sa.ForeignKey("filiais.id"), nullable=False),
        sa.Column("chave_acesso", sa.String(44), nullable=False, unique=True),
        sa.Column("numero_nota", sa.String(20), nullable=False),
        sa.Column("serie", sa.String(5), nullable=False),
        sa.Column("cnpj_emitente", sa.String(18), nullable=False),
        sa.Column("nome_emitente", sa.String(150), nullable=False),
        sa.Column("data_emissao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("xml_raw", sa.Text(), nullable=False),
        sa.Column("status", status_nfe_entrada_enum_col, nullable=False, server_default="aguardando_confirmacao"),
        sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("confirmado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmado_por_operador_id", UUID(as_uuid=True), sa.ForeignKey("operadores.id"), nullable=True),
    )

    op.create_table(
        "notas_fiscais_entrada_itens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "nota_id", UUID(as_uuid=True), sa.ForeignKey("notas_fiscais_entrada.id", ondelete="CASCADE"), nullable=False
        ),
        # NULL se o produto não foi encontrado no cadastro (NCM ou nome não bate).
        sa.Column("produto_id", UUID(as_uuid=True), sa.ForeignKey("produtos.id"), nullable=True),
        sa.Column("ncm", sa.String(10), nullable=False),
        sa.Column("descricao_produto", sa.String(200), nullable=False),
        sa.Column("numero_lote", sa.String(40), nullable=True),
        sa.Column("data_validade", sa.Date(), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("custo_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total_item", sa.Numeric(12, 2), nullable=False),
        sa.Column("v_icms_st", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("p_pis", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("v_pis", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("p_cofins", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("v_cofins", sa.Numeric(10, 2), nullable=False, server_default="0"),
        # Preenchido só após confirmação (endpoint app_backend) — nunca pelo agente.
        sa.Column("lote_criado_id", UUID(as_uuid=True), sa.ForeignKey("lotes.id"), nullable=True),
        sa.Column("status_produto", status_item_nfe_enum_col, nullable=False, server_default="identificado"),
        sa.CheckConstraint("quantidade > 0", name="chk_notas_fiscais_entrada_itens_quantidade_positiva"),
    )
    op.create_index(
        "idx_notas_fiscais_entrada_itens_nota", "notas_fiscais_entrada_itens", ["nota_id"]
    )
    op.create_index("idx_notas_fiscais_entrada_status", "notas_fiscais_entrada", ["status"])

    # =========================================================================
    # Role de banco + GRANTs mínimos (mesmo padrão de 0011_roles_grants.sql)
    # =========================================================================
    op.execute(
        "DO $$ BEGIN "
        "CREATE ROLE agente_tributario LOGIN PASSWORD 'CHANGE_ME_TRIBUTARIO'; "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO agente_tributario")
    # Baseline: nenhum privilégio implícito — só o que os GRANTs abaixo derem.
    op.execute("REVOKE ALL ON notas_fiscais_entrada, notas_fiscais_entrada_itens FROM PUBLIC")

    op.execute("GRANT SELECT ON produtos, principios_ativos, filiais TO agente_tributario")
    op.execute("GRANT SELECT, INSERT ON notas_fiscais_entrada_itens TO agente_tributario")
    op.execute("GRANT SELECT, INSERT, UPDATE ON notas_fiscais_entrada TO agente_tributario")
    op.execute("GRANT INSERT ON logs_auditoria TO agente_tributario")

    # =========================================================================
    # RLS (defesa em profundidade, mesmo padrão da migration 0002): tabela
    # nova não herda GRANT antigo nenhum (nem o "SELECT ON ALL TABLES" legado
    # do agente_orquestrador em 0011 — esse GRANT só alcançou as tabelas que
    # já existiam quando rodou), mas habilitamos RLS + policy explícita mesmo
    # assim, pra nunca depender só do GRANT de tabela.
    # =========================================================================
    op.execute("ALTER TABLE notas_fiscais_entrada ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notas_fiscais_entrada_itens ENABLE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY all_backend ON notas_fiscais_entrada FOR ALL TO app_backend USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY all_backend ON notas_fiscais_entrada_itens FOR ALL TO app_backend USING (true) WITH CHECK (true)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON notas_fiscais_entrada, notas_fiscais_entrada_itens TO app_backend"
    )

    op.execute(
        "CREATE POLICY sel_ins_upd_tributario ON notas_fiscais_entrada "
        "FOR ALL TO agente_tributario USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY sel_ins_tributario ON notas_fiscais_entrada_itens "
        "FOR ALL TO agente_tributario USING (true) WITH CHECK (true)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sel_ins_tributario ON notas_fiscais_entrada_itens")
    op.execute("DROP POLICY IF EXISTS sel_ins_upd_tributario ON notas_fiscais_entrada")
    op.execute("DROP POLICY IF EXISTS all_backend ON notas_fiscais_entrada_itens")
    op.execute("DROP POLICY IF EXISTS all_backend ON notas_fiscais_entrada")

    op.execute("REVOKE ALL ON notas_fiscais_entrada, notas_fiscais_entrada_itens FROM agente_tributario")
    op.execute("REVOKE ALL ON notas_fiscais_entrada, notas_fiscais_entrada_itens FROM app_backend")
    op.execute("REVOKE ALL ON produtos, principios_ativos, filiais FROM agente_tributario")
    op.execute("REVOKE INSERT ON logs_auditoria FROM agente_tributario")
    op.execute("REVOKE USAGE ON SCHEMA public FROM agente_tributario")
    # A role em si (CREATE ROLE) não é derrubada aqui de propósito — mesma
    # convenção do resto do projeto: nunca houve um downgrade que faça DROP
    # ROLE (evita quebrar conexões ativas de outros ambientes usando a mesma
    # role por engano). Se precisar remover de fato, faça manualmente.

    op.drop_index("idx_notas_fiscais_entrada_status", table_name="notas_fiscais_entrada")
    op.drop_index("idx_notas_fiscais_entrada_itens_nota", table_name="notas_fiscais_entrada_itens")
    op.drop_table("notas_fiscais_entrada_itens")
    op.drop_table("notas_fiscais_entrada")

    op.drop_index("idx_produtos_ncm", table_name="produtos")
    op.drop_column("produtos", "ncm")

    # Postgres não permite remover um valor de ENUM (DROP VALUE não existe) —
    # downgrade não reverte os ALTER TYPE ADD VALUE, mesma limitação inerente
    # de qualquer migration deste projeto que adicione valor de enum.
    sa.Enum(name="status_item_nfe_enum").drop(op.get_bind())
    sa.Enum(name="status_nfe_entrada_enum").drop(op.get_bind())
