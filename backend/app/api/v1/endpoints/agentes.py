import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agents.service import run_analise_estoque, run_processar_nfe_email
from app.core.auth import get_current_operador
from app.core.rate_limit import limiter
from app.schemas.agentes import AnaliseEstoqueRequest, AnaliseEstoqueResponse
from app.schemas.notas_entrada import ProcessarNFeEmailResponse

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


@router.post("/processar-nfe-email", response_model=ProcessarNFeEmailResponse)
@limiter.limit("3/minute")
async def processar_nfe_email(
    request: Request, _operador=Depends(get_current_operador)
) -> ProcessarNFeEmailResponse:
    """Dispara o Agente Tributário (Bloco 1): lê os emails de NF-e não lidos,
    identifica os produtos e grava cada nota como 'aguardando_confirmacao'
    — nunca aplica a entrada em estoque sozinho (ver POST
    /notas-entrada/{id}/confirmar).

    3/minuto (mesmo espírito do SEC-02): cada chamada instancia um Crew
    inteiro com LLM real (modelo Pro, mais caro que o Flash do Atendente) e
    ainda abre uma conexão IMAP — rate limit aqui é de custo, não só de
    tráfego.

    `_operador` já vem exigido pelo `dependencies=[...]` de nível de router
    (app/api/v1/router.py) — repetido aqui como documentação executável,
    mesmo padrão de PATCH /produtos/{id}/tarja: este endpoint é caro demais
    pra depender só de alguém lembrar de configurar o router certo.
    """
    try:
        return await asyncio.to_thread(run_processar_nfe_email)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
