"""FASE 4: wrapper único em volta de Crew.kickoff() cobrindo três
preocupações que são, na prática, a mesma pergunta feita de três jeitos —
"essa chamada ao LLM terminou bem, e o que aconteceu de fato?":

- LLM-04: `resultado.pydantic` pode vir None (o LLM não seguiu o schema
  pedido). Tenta de novo (crew NOVO, não reaproveitado) antes de desistir.
- LLM-05: crew.kickoff() é uma chamada de rede sem timeout embutido que dá
  pra configurar de fora. Timeout duro via thread auxiliar.
- LLM-08/QA-03: toda chamada registra modelo real, tokens e latência —
  sem isso a auditoria mente sobre o que decidiu, e não há dado pra decidir
  infraestrutura.
"""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass

from crewai import Crew
from crewai.crews.crew_output import CrewOutput

from app.agents.config import get_agent_settings

logger = logging.getLogger(__name__)


@dataclass
class ExecucaoCrew:
    resultado: CrewOutput | None  # None = todas as tentativas falharam (timeout ou pydantic sempre None)
    modelo_llm: str
    latencia_ms: int
    tokens_totais: int | None
    tentativas: int
    timeout: bool


def executar_crew(criar_crew: Callable[[], Crew], *, modelo_llm: str, tentativas_max: int = 2) -> ExecucaoCrew:
    """`criar_crew` é uma FÁBRICA, não um Crew pronto — o retry (LLM-04)
    precisa de Agent/Task/Crew novos a cada tentativa; reaproveitar a mesma
    instância entre tentativas mistura estado de execução da tentativa
    anterior (histórico de mensagens, tool calls) com a nova.

    Nota sobre o timeout (LLM-05): Python não mata uma thread à força. Se
    `crew.kickoff()` estourar o timeout, esta função devolve controle (e o
    chamador aplica o fallback seguro), mas a chamada ao LLM que já estava em
    voo continua rodando em segundo plano até terminar sozinha — é o
    trade-off padrão de timeout "soft" sobre uma chamada bloqueante sem
    cancelamento cooperativo. A alternativa (matar via processo separado) é
    peso demais pra esse caso.

    IMPORTANTE: `ThreadPoolExecutor` usado como context manager (`with ...:`)
    bloqueia no `__exit__` até a thread terminar (`shutdown(wait=True)`) —
    isso anularia o timeout inteiro, porque a função só devolveria controle
    depois que o kickoff() lento já tivesse acabado sozinho. Por isso o
    executor é criado e desligado manualmente com `wait=False`: a thread
    continua rodando em segundo plano (e é reaproveitada por join automático
    no encerramento do processo, via o atexit hook padrão do módulo
    concurrent.futures), mas esta função retorna assim que o timeout estoura.
    """
    timeout_seconds = get_agent_settings().crew_timeout_seconds
    inicio = time.monotonic()
    resultado: CrewOutput | None = None
    houve_timeout = False
    tentativa = 0

    for tentativa in range(1, tentativas_max + 1):
        houve_timeout = False
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(lambda: criar_crew().kickoff())
            try:
                resultado = future.result(timeout=timeout_seconds)
            except FutureTimeoutError:
                houve_timeout = True
                resultado = None
            except Exception:
                # "Não silenciar" (LLM-04): uma exceção real de dentro do
                # kickoff() (bug de tool, erro de rede não relacionado a
                # timeout, etc.) não pode desaparecer sem rastro só porque o
                # caminho de fallback tem a mesma forma de "resultado=None"
                # de um pydantic ausente — loga com stack trace antes de
                # seguir pro fallback/retry.
                logger.exception("crew.kickoff() levantou exceção na tentativa %d/%d", tentativa, tentativas_max)
                resultado = None
        finally:
            executor.shutdown(wait=False)

        if resultado is not None and resultado.pydantic is not None:
            break

    latencia_ms = int((time.monotonic() - inicio) * 1000)
    sucesso = resultado is not None and resultado.pydantic is not None
    tokens_totais = resultado.token_usage.total_tokens if resultado is not None else None

    return ExecucaoCrew(
        resultado=resultado if sucesso else None,
        modelo_llm=modelo_llm,
        latencia_ms=latencia_ms,
        tokens_totais=tokens_totais,
        tentativas=tentativa,
        timeout=houve_timeout,
    )
