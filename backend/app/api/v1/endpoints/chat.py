import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from app.agents.service import run_atendimento
from app.core.rate_limit import limiter
from app.schemas.chat import ChatAtendimentoRequest, ChatAtendimentoResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/atendimento", response_model=ChatAtendimentoResponse)
@limiter.limit("10/minute")
async def atendimento(request: Request, payload: ChatAtendimentoRequest) -> ChatAtendimentoResponse:
    """Fluxo do Agente Atendente. Duas fases via o mesmo endpoint:

    - confirmar_compra=false: pesquisa clínica (estoque + substitutos MIP) e devolve
      sugestões, sem tocar o banco além do log de auditoria.
    - confirmar_compra=true (com produto_id): processa pagamento/nota fiscal mockados
      e grava a venda. Reenvie o mesmo sessao_id devolvido na primeira chamada para
      manter as duas fases ligadas na auditoria.

    FASE 1 (SEC-02): 10 chamadas/minuto por IP — cada uma instancia um Crew
    inteiro com LLM real, então isto é rate limit de custo, não só de tráfego.
    """
    try:
        return await asyncio.to_thread(run_atendimento, payload)
    except PermissionError as exc:
        # LGPD-03: cliente_id informado sem consentimento registrado.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
