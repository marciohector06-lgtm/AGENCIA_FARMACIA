"""Seleciona qual ERPAdapter esta instalação usa.

Hoje só existe o MockAdapter (ambiente de simulação, F0-02). Trocar de ERP em
produção é escrever um adaptador novo que implemente ERPAdapter (base.py) e
adicionar uma linha aqui — nenhuma tool, agente ou migration muda.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.integrations.base import ERPAdapter
from app.integrations.mock_adapter import MockAdapter

ORIGEM_PADRAO = "mock"


@lru_cache
def get_erp_adapter() -> ERPAdapter:
    provider = get_settings().erp_provider
    if provider == "mock":
        return MockAdapter()
    raise RuntimeError(f"ERP_PROVIDER='{provider}' não tem adaptador implementado ainda.")
