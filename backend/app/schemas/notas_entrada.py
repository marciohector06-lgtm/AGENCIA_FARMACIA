import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StatusItemNfeEnum, StatusNfeEntradaEnum


class NotaFiscalEntradaItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    produto_id: uuid.UUID | None = None
    ncm: str
    descricao_produto: str
    numero_lote: str | None = None
    data_validade: date | None = None
    quantidade: int
    custo_unitario: Decimal
    valor_total_item: Decimal
    v_icms_st: Decimal
    p_pis: Decimal
    v_pis: Decimal
    p_cofins: Decimal
    v_cofins: Decimal
    lote_criado_id: uuid.UUID | None = None
    status_produto: StatusItemNfeEnum


class NotaFiscalEntradaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filial_id: uuid.UUID
    chave_acesso: str
    numero_nota: str
    serie: str
    cnpj_emitente: str
    nome_emitente: str
    data_emissao: datetime
    valor_total: Decimal
    status: StatusNfeEntradaEnum
    recebido_em: datetime
    confirmado_em: datetime | None = None
    confirmado_por_operador_id: uuid.UUID | None = None


class NotaFiscalEntradaDetalhe(NotaFiscalEntradaRead):
    itens: list[NotaFiscalEntradaItemRead] = Field(default_factory=list)


class ConfirmarEntradaResponse(BaseModel):
    nota_id: uuid.UUID
    lotes_criados: int
    lotes_atualizados: int
    itens_ignorados: int
    valor_total_entrada: Decimal
    log_auditoria_id: uuid.UUID


class ProcessarNFeEmailResponse(BaseModel):
    notas_processadas: int
    resumo: str
    log_auditoria_id: uuid.UUID | None = None
