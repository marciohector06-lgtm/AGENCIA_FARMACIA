import asyncio

from fastapi import APIRouter, HTTPException, status

from app.agents.service import run_atendimento
from app.schemas.chat import ChatAtendimentoRequest, ChatAtendimentoResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/atendimento", response_model=ChatAtendimentoResponse)
async def atendimento(payload: ChatAtendimentoRequest) -> ChatAtendimentoResponse:
    """Fluxo do Agente Atendente. Duas fases via o mesmo endpoint:

    - confirmar_compra=false: pesquisa clínica (estoque + substitutos MIP) e devolve
      sugestões, sem tocar o banco além do log de auditoria.
    - confirmar_compra=true (com produto_id): processa pagamento/nota fiscal mockados
      e grava a venda. Reenvie o mesmo sessao_id devolvido na primeira chamada para
      manter as duas fases ligadas na auditoria.
    """
    try:
        return await asyncio.to_thread(run_atendimento, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
