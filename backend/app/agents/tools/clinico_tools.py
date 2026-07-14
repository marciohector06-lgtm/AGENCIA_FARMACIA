from crewai.tools import BaseTool
from sqlalchemy import text

from app.agents.config import AgentRole
from app.agents.db_sync import agent_session


class BuscarProdutoPorNomeTool(BaseTool):
    name: str = "buscar_produto_por_nome"
    description: str = (
        "Busca produtos cadastrados por nome comercial (busca parcial, case-insensitive). "
        "A role de banco usada por esta ferramenta já filtra por RLS: só retorna produtos "
        "com tarja='isento' (MIP) e ativos — NUNCA use um nome de produto que não veio "
        "desta ferramenta ou de buscar_principio_ativo."
    )
    role: AgentRole = AgentRole.ATENDENTE

    def _run(self, nome: str) -> list[dict]:
        with agent_session(self.role) as session:
            rows = session.execute(
                text(
                    """
                    SELECT id, nome_comercial, forma_farmaceutica, via_administracao,
                           concentracao_valor, concentracao_unidade, preco_tabela, principio_ativo_id
                    FROM produtos
                    WHERE nome_comercial ILIKE '%' || :nome || '%'
                    ORDER BY nome_comercial
                    LIMIT 10
                    """
                ),
                {"nome": nome},
            )
            return [dict(row._mapping) for row in rows]


class BuscarPrincipioAtivoTool(BaseTool):
    name: str = "buscar_principio_ativo"
    description: str = (
        "Busca princípios ativos por nome (busca parcial). Retorna id, classe "
        "terapêutica e contraindicações gerais. Use antes de sugerir qualquer "
        "substituto — a sugestão final deve sempre se basear no principio_ativo_id "
        "retornado aqui, nunca em um nome inventado."
    )
    role: AgentRole = AgentRole.ATENDENTE

    def _run(self, nome: str) -> list[dict]:
        with agent_session(self.role) as session:
            rows = session.execute(
                text(
                    """
                    SELECT id, nome, nome_dcb, classe_terapeutica, contraindicacoes_gerais
                    FROM principios_ativos
                    WHERE nome ILIKE '%' || :nome || '%'
                    ORDER BY nome
                    LIMIT 10
                    """
                ),
                {"nome": nome},
            )
            return [dict(row._mapping) for row in rows]


class BuscarProdutosSubstituiveisTool(BaseTool):
    name: str = "buscar_produtos_substituiveis"
    description: str = (
        "Dado um produto_id, retorna outros produtos MIP com o MESMO princípio ativo, "
        "forma farmacêutica e via de administração — candidatos válidos a substituto "
        "genérico quando o produto original está sem estoque."
    )
    role: AgentRole = AgentRole.ATENDENTE

    def _run(self, produto_id: str) -> list[dict]:
        with agent_session(self.role) as session:
            rows = session.execute(
                text(
                    """
                    SELECT produto_substituto_id, produto_substituto_nome,
                           concentracao_origem, concentracao_substituto, concentracao_unidade
                    FROM vw_produtos_substituiveis
                    WHERE produto_origem_id = :produto_id
                    """
                ),
                {"produto_id": produto_id},
            )
            return [dict(row._mapping) for row in rows]


class ConsultarRestricoesUsoTool(BaseTool):
    name: str = "consultar_restricoes_uso"
    description: str = (
        "Retorna restrições de uso (gestante, lactante, pediátrico, idoso, etc.) de um "
        "princípio ativo. Consulte SEMPRE antes de recomendar, para alertar o cliente "
        "sobre cautelas relevantes — nunca omita uma contraindicação encontrada aqui."
    )
    role: AgentRole = AgentRole.ATENDENTE

    def _run(self, principio_ativo_id: str) -> list[dict]:
        with agent_session(self.role) as session:
            rows = session.execute(
                text(
                    """
                    SELECT tipo_restricao, nivel, descricao
                    FROM restricoes_uso_principio_ativo
                    WHERE principio_ativo_id = :principio_ativo_id
                    """
                ),
                {"principio_ativo_id": principio_ativo_id},
            )
            return [dict(row._mapping) for row in rows]


class ConsultarInteracoesTool(BaseTool):
    name: str = "consultar_interacoes"
    description: str = (
        "Verifica interações medicamentosas conhecidas entre o princípio ativo do produto que "
        "você está prestes a recomendar e os medicamentos que o cliente informou já estar usando. "
        "Recebe principio_ativo_id (do produto candidato) e medicamentos_em_uso (lista de nomes "
        "livres, como o cliente descreveu, ex.: ['varfarina', 'losartana']). Chame SEMPRE que o "
        "cliente tiver informado medicamentos em uso, antes de recomendar qualquer produto — "
        "CLIN-05 bloqueia a resposta se isso não acontecer. Retorna as interações encontradas "
        "(com gravidade) e também quais nomes da lista não foram reconhecidos na base — avise o "
        "cliente sobre nomes não reconhecidos em vez de presumir que estão seguros."
    )
    role: AgentRole = AgentRole.ATENDENTE

    def _run(self, principio_ativo_id: str, medicamentos_em_uso: list[str]) -> dict:
        if not medicamentos_em_uso:
            return {"interacoes": [], "nao_reconhecidos": []}

        interacoes: list[dict] = []
        nao_reconhecidos: list[str] = []
        with agent_session(self.role) as session:
            for nome in medicamentos_em_uso:
                outro = session.execute(
                    text("SELECT id, nome FROM principios_ativos WHERE nome ILIKE '%' || :nome || '%' LIMIT 1"),
                    {"nome": nome},
                ).first()
                if outro is None:
                    nao_reconhecidos.append(nome)
                    continue
                if str(outro.id) == principio_ativo_id:
                    continue  # mesmo princípio ativo do produto sugerido, não é interação entre dois diferentes

                # Ordem canônica exigida por interacoes_medicamentosas (chk_ordem_canonica,
                # migration 0004): a_id < b_id. Comparação textual de UUID canônico
                # (uuid.UUID minúsculo com traços nas mesmas posições) bate com a
                # comparação nativa de UUID do Postgres.
                a_id, b_id = sorted([principio_ativo_id, str(outro.id)])
                interacao = session.execute(
                    text(
                        """
                        SELECT gravidade, descricao, fonte
                        FROM interacoes_medicamentosas
                        WHERE principio_ativo_a_id = :a AND principio_ativo_b_id = :b
                        """
                    ),
                    {"a": a_id, "b": b_id},
                ).first()
                if interacao is not None:
                    interacoes.append(
                        {
                            "medicamento_em_uso": nome,
                            "principio_ativo_reconhecido": outro.nome,
                            "gravidade": interacao.gravidade,
                            "descricao": interacao.descricao,
                            "fonte": interacao.fonte,
                        }
                    )

        return {"interacoes": interacoes, "nao_reconhecidos": nao_reconhecidos}
