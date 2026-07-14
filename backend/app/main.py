from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

app = FastAPI(title="Farmacia MAS API", version="0.1.0")
# FASE 1 (SEC-02): limitador por IP. Cada POST /chat/atendimento instancia um
# Crew inteiro com Gemini 2.5 Pro — sem isso, é DoS de custo direto na fatura.
# Números conservadores de largada (10/min chat, 3/min análise de estoque,
# que dispara DOIS crews em sequência) — ajustamos com dado real de uso.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# FASE 1 (SEC-09): allow_credentials=True só faz sentido pra auth via cookie
# — usamos Bearer token no header Authorization, que não depende de modo
# "credentialed" do CORS. Métodos e headers explícitos em vez de "*": a
# combinação de "*" nos três com credentials=True é a configuração mais
# permissiva possível, e nada aqui precisa disso.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
