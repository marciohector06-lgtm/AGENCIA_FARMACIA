import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from app.agents.service import run_analise_estoque
from app.core.rate_limit import limiter
from app.schemas.agentes import AnaliseEstoqueRequest, AnaliseEstoqueResponse

router = APIRouter(prefix="/agentes", tags=["agentes"])


@router.post("/analise-estoque", response_model=AnaliseEstoqueResponse)
@limiter.limit("3/minute")
async def analise_estoque(request: Request, payload: AnaliseEstoqueRequest) -> AnaliseEstoqueResponse:
    """Dispara o fluxo Gerente de Estoque -> Financeiro: identifica produtos vencendo,
    propõe descontos com base em giro real e exige aprovação financeira por margem.
    Cada decisão autônoma é gravada em logs_auditoria antes da resposta retornar.

    FASE 1 (SEC-02): 3 chamadas/minuto por IP — dispara DOIS crews em
    sequência (Gerente + Financeiro), o dobro do custo de uma chamada de chat.
    """
    try:
        return await asyncio.to_thread(run_analise_estoque, payload.filial_id, payload.dias_vencimento)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
