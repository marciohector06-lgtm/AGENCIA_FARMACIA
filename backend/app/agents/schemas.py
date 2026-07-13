"""Schemas de saída estruturada dos Tasks do CrewAI (output_pydantic).

Forçam o LLM a devolver algo parseável de forma determinística, em vez de a
camada de serviço depender de regex/parsing de texto livre para decidir o que
gravar no banco.
"""

from pydantic import BaseModel, Field


class PropostaGerada(BaseModel):
    produto_id: str
    produto_nome: str
    lote_id: str
    precificacao_id: str
    preco_anterior: float
    preco_novo: float
    motivo: str


class AnaliseEstoqueGerenteOutput(BaseModel):
    propostas: list[PropostaGerada] = Field(default_factory=list)
    resumo: str


class DecisaoFinanceira(BaseModel):
    precificacao_id: str
    aprovado: bool
    margem_resultante: float | None = None
    justificativa: str


class AnaliseEstoqueFinanceiroOutput(BaseModel):
    decisoes: list[DecisaoFinanceira] = Field(default_factory=list)
    resumo: str


class ProdutoSugerido(BaseModel):
    produto_id: str
    nome_comercial: str
    disponivel: bool
    preco: float
    motivo_sugestao: str


class RespostaAtendimentoOutput(BaseModel):
    resposta_texto: str
    principio_ativo_id: str | None = None
    produtos_sugeridos: list[ProdutoSugerido] = Field(default_factory=list)


class ConfirmacaoCompraOutput(BaseModel):
    sucesso: bool
    resposta_texto: str
    transacao_id: str | None = None
    nfe_chave: str | None = None
