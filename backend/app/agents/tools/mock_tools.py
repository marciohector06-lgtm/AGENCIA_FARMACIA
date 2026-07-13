import time
import uuid

from crewai.tools import BaseTool


class ProcessarPagamentoMockTool(BaseTool):
    name: str = "processar_pagamento_mock"
    description: str = (
        "Simula o processamento de um pagamento (nunca chama um gateway real). "
        "Use somente depois que o cliente confirmar explicitamente a compra de um produto e quantidade."
    )

    def _run(self, valor_total: float, forma_pagamento: str = "cartao") -> dict:
        time.sleep(2)  # simula latência de um gateway de pagamento real
        return {
            "status": "aprovado",
            "transacao_id": f"mock_{uuid.uuid4().hex[:12]}",
            "valor_total": valor_total,
            "forma_pagamento": forma_pagamento,
        }


class GerarNotaFiscalMockTool(BaseTool):
    name: str = "gerar_nota_fiscal_mock"
    description: str = (
        "Simula a emissão de uma nota fiscal eletrônica (nunca chama a SEFAZ real). "
        "Use somente depois que o pagamento tiver sido aprovado por processar_pagamento_mock."
    )

    def _run(self, transacao_id: str, valor_total: float) -> dict:
        time.sleep(2)  # simula latência de emissão junto à SEFAZ real
        return {
            "status": "aprovado",
            "nfe": "simulada",
            "chave_acesso": f"mock_nfe_{uuid.uuid4().hex[:20]}",
            "transacao_id": transacao_id,
            "valor_total": valor_total,
        }
