import uuid

from pydantic import BaseModel, Field


class ChatAtendimentoRequest(BaseModel):
    sessao_id: uuid.UUID | None = None
    filial_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    # SEC-08: sem teto, um cliente podia mandar um texto gigante e estourar
    # contexto/custo do LLM numa única chamada.
    mensagem: str = Field(max_length=2000)
    confirmar_compra: bool = False
    produto_id: uuid.UUID | None = None
    lote_id: uuid.UUID | None = None
    # QA-06: mesma faixa em todo schema com esse campo (0 e >999 viravam 422
    # já antes por outro caminho em alguns endpoints; aqui não havia limite
    # nenhum).
    quantidade: int = Field(default=1, ge=1, le=999)

    # CLIN-04: perfil clínico opcional — o farmacêutico/atendente preenche o
    # que souber, nunca obrigatório. Alimenta ConsultarInteracoesTool
    # (medicamentos_em_uso) e consultar_restricoes_uso (gestante/lactante/
    # idade). Nomes livres em medicamentos_em_uso, exatamente como a pessoa
    # descreveu — a tool é quem resolve pra um princípio ativo conhecido.
    medicamentos_em_uso: list[str] = Field(default_factory=list)
    gestante: bool = False
    lactante: bool = False
    idade: int | None = Field(default=None, ge=0, le=130)


class ProdutoSugeridoResponse(BaseModel):
    produto_id: uuid.UUID
    nome_comercial: str
    disponivel: bool
    preco: float
    motivo_sugestao: str


class ChatAtendimentoResponse(BaseModel):
    sessao_id: uuid.UUID
    resposta: str
    produtos_sugeridos: list[ProdutoSugeridoResponse]
    venda_id: uuid.UUID | None = None
    log_auditoria_id: uuid.UUID | None = None
    # CLIN-06: preenchido deterministicamente por service.py (DISCLAIMER_PADRAO),
    # nunca pelo LLM — sempre presente, em toda resposta do fluxo de atendimento.
    disclaimer: str = ""
