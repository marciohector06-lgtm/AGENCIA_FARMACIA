import asyncio

from fastapi import APIRouter, HTTPException, status

from app.agents.service import run_analise_estoque
from app.schemas.agentes import AnaliseEstoqueRequest, AnaliseEstoqueResponse

router = APIRouter(prefix="/agentes", tags=["agentes"])


@router.post("/analise-estoque", response_model=AnaliseEstoqueResponse)
async def analise_estoque(payload: AnaliseEstoqueRequest) -> AnaliseEstoqueResponse:
    """Dispara o fluxo Gerente de Estoque -> Financeiro: identifica produtos vencendo,
    propõe descontos com base em giro real e exige aprovação financeira por margem.
    Cada decisão autônoma é gravada em logs_auditoria antes da resposta retornar.
    """
    try:
        return await asyncio.to_thread(run_analise_estoque, payload.filial_id, payload.dias_vencimento)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
