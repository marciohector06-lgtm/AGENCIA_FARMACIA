import asyncio
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.audit import registrar_auditoria
from app.agents.config import AgentRole
from app.api.v1.pagination import LimitQuery, SkipQuery
from app.core.auth import OperadorAutenticado, get_current_operador
from app.core.db import get_db
from app.models.enums import StatusLoteEnum, StatusNfeEntradaEnum, TipoDecisaoEnum, TipoMovimentacaoEnum
from app.models.estoque import Estoque
from app.models.lote import Lote
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.models.nota_fiscal_entrada import NotaFiscalEntrada, NotaFiscalEntradaItem
from app.schemas.notas_entrada import (
    ConfirmarEntradaResponse,
    NotaFiscalEntradaDetalhe,
    NotaFiscalEntradaItemRead,
    NotaFiscalEntradaRead,
)

router = APIRouter(prefix="/notas-entrada", tags=["notas-entrada"])


@router.get("", response_model=list[NotaFiscalEntradaRead])
async def listar_notas_entrada(
    skip: SkipQuery = 0,
    limit: LimitQuery = 100,
    status_nota: StatusNfeEntradaEnum | None = None,
    filial_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[NotaFiscalEntrada]:
    stmt = select(NotaFiscalEntrada).order_by(NotaFiscalEntrada.recebido_em.desc())
    if status_nota is not None:
        stmt = stmt.where(NotaFiscalEntrada.status == status_nota)
    if filial_id is not None:
        stmt = stmt.where(NotaFiscalEntrada.filial_id == filial_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{nota_id}", response_model=NotaFiscalEntradaDetalhe)
async def obter_nota_entrada(nota_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> NotaFiscalEntrada:
    nota = await db.get(NotaFiscalEntrada, nota_id)
    if nota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal de entrada não encontrada")
    itens = (
        await db.execute(select(NotaFiscalEntradaItem).where(NotaFiscalEntradaItem.nota_id == nota_id))
    ).scalars().all()
    # A ORM não declara relationship() entre as duas tabelas (o resto do
    # projeto também não usa relationship() em lugar nenhum — prefere query
    # explícita), então montamos a resposta combinando as duas queries à mão
    # em vez de tentar validar 'itens' diretamente a partir do objeto ORM.
    return NotaFiscalEntradaDetalhe(
        **NotaFiscalEntradaRead.model_validate(nota, from_attributes=True).model_dump(),
        itens=[NotaFiscalEntradaItemRead.model_validate(item, from_attributes=True) for item in itens],
    )


@router.post("/{nota_id}/confirmar", response_model=ConfirmarEntradaResponse)
async def confirmar_entrada_nfe(
    nota_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    operador: OperadorAutenticado = Depends(get_current_operador),
) -> ConfirmarEntradaResponse:
    """Único lugar do sistema que aplica de fato a entrada de uma NF-e
    processada pelo Agente Tributário: cria/atualiza lote, credita estoque
    (sempre via lançamento em movimentacoes_estoque — SEC-11, nunca um UPDATE
    solto) e marca a nota como confirmada. Roda inteiro como app_backend —
    agente_tributario nunca tem GRANT em lotes/estoque/movimentacoes_estoque.

    Atômico (ou tudo ou nada): nenhum commit intermediário acontece antes do
    único `db.commit()` no fim — se qualquer item levantar uma exceção no
    meio do loop, a sessão inteira é revertida e nada foi persistido, mesma
    garantia de _debitar_estoque_venda no fluxo do Atendente.
    """
    nota = (
        await db.execute(select(NotaFiscalEntrada).where(NotaFiscalEntrada.id == nota_id).with_for_update())
    ).scalar_one_or_none()
    if nota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota fiscal de entrada não encontrada")
    if nota.status != StatusNfeEntradaEnum.aguardando_confirmacao:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nota já está com status '{nota.status.value}' — só é possível confirmar notas 'aguardando_confirmacao'.",
        )

    itens = (
        await db.execute(select(NotaFiscalEntradaItem).where(NotaFiscalEntradaItem.nota_id == nota_id))
    ).scalars().all()

    lotes_criados = 0
    lotes_atualizados = 0
    itens_ignorados = 0

    for item in itens:
        # Itens sem produto_id (não identificados no cadastro) e itens sem
        # numero_lote/data_validade suficientes para criar um lote válido
        # ficam de fora da entrada de estoque — seguem gravados na nota para
        # conferência manual, mas não geram lote/estoque/movimentação
        # (mesmo princípio do requisito original "produto_id=NULL é
        # ignorado", estendido às duas outras colunas nullable que um Lote
        # de verdade exige).
        if item.produto_id is None or not item.numero_lote or item.data_validade is None:
            itens_ignorados += 1
            continue

        lote = (
            await db.execute(
                select(Lote)
                .where(Lote.produto_id == item.produto_id, Lote.numero_lote == item.numero_lote)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if lote is None:
            lote = Lote(
                produto_id=item.produto_id,
                numero_lote=item.numero_lote,
                # NF-e não traz data de fabricação (só validade) — usar a data
                # de recebimento é a aproximação mais honesta disponível; quem
                # decide sobre validade pra FEFO é sempre data_validade, nunca
                # esta.
                data_fabricacao=date.today(),
                data_validade=item.data_validade,
                quantidade_recebida=item.quantidade,
                custo_unitario=item.custo_unitario,
                status=StatusLoteEnum.disponivel,
                origem="manual",
            )
            db.add(lote)
            await db.flush()
            lotes_criados += 1
        else:
            lotes_atualizados += 1

        estoque_atual = (
            await db.execute(
                select(Estoque)
                .where(Estoque.filial_id == nota.filial_id, Estoque.lote_id == lote.id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if estoque_atual is None:
            nova_quantidade = item.quantidade
            estoque_atual = Estoque(
                filial_id=nota.filial_id,
                lote_id=lote.id,
                quantidade_atual=nova_quantidade,
                quantidade_reservada=0,
                origem="manual",
            )
            db.add(estoque_atual)
            await db.flush()
        else:
            nova_quantidade = estoque_atual.quantidade_atual + item.quantidade
            estoque_atual.quantidade_atual = nova_quantidade

        db.add(
            MovimentacaoEstoque(
                estoque_id=estoque_atual.id,
                tipo=TipoMovimentacaoEnum.entrada_nfe,
                quantidade_delta=item.quantidade,
                quantidade_resultante=nova_quantidade,
                motivo=f"NF-e {nota.numero_nota} — {nota.nome_emitente}",
            )
        )

        item.lote_criado_id = lote.id

    nota.status = StatusNfeEntradaEnum.confirmada
    nota.confirmado_em = datetime.now(timezone.utc)
    nota.confirmado_por_operador_id = uuid.UUID(operador.operador_id)

    await db.commit()

    valor_total_entrada = sum(
        (item.custo_unitario * item.quantidade for item in itens if item.lote_criado_id is not None),
        start=Decimal("0"),
    )

    # Domínio da decisão é o próprio Agente Tributário (a nota que está sendo
    # confirmada é artefato dele) — diferente do precedente de
    # PATCH /produtos/{id}/tarja, que usa ORQUESTRADOR por não ter uma role
    # de domínio melhor disponível na época. agente_tributario tem GRANT de
    # INSERT em logs_auditoria (migration 0005) exatamente para isto.
    log_id = await asyncio.to_thread(
        registrar_auditoria,
        role=AgentRole.TRIBUTARIO,
        tipo_decisao=TipoDecisaoEnum.entrada_nfe_processada,
        entidade_afetada="notas_fiscais_entrada",
        entidade_id=nota.id,
        decisao_tomada=(
            f"Entrada confirmada por operador: {lotes_criados} lote(s) criado(s), "
            f"{lotes_atualizados} atualizado(s), {itens_ignorados} item(ns) ignorado(s)."
        ),
        dados_base={
            "nota_id": str(nota.id),
            "numero_nota": nota.numero_nota,
            "lotes_criados": lotes_criados,
            "lotes_atualizados": lotes_atualizados,
            "itens_ignorados": itens_ignorados,
            "valor_total_entrada": float(valor_total_entrada),
            "operador_id": operador.operador_id,
            "operador_email": operador.email,
        },
    )

    return ConfirmarEntradaResponse(
        nota_id=nota.id,
        lotes_criados=lotes_criados,
        lotes_atualizados=lotes_atualizados,
        itens_ignorados=itens_ignorados,
        valor_total_entrada=valor_total_entrada,
        log_auditoria_id=log_id,
    )
