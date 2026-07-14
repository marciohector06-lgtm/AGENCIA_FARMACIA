"""FASE 1 (SEC-02): limiter num módulo próprio, não em main.py — os endpoints
precisam importar `limiter` pra decorar suas rotas, e main.py importa
api_router (que importa os endpoints); definir o Limiter em main.py criaria
import circular.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
