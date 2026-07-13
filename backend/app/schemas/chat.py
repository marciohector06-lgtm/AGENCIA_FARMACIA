import uuid

from pydantic import BaseModel


class ChatAtendimentoRequest(BaseModel):
    sessao_id: uuid.UUID | None = None
    filial_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    mensagem: str
    confirmar_compra: bool = False
    produto_id: uuid.UUID | None = None
    lote_id: uuid.UUID | None = None
    quantidade: int = 1


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
