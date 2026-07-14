"""Guarda de escrita por origem (FASE 0 / migration 0019).

Uma linha com origem != 'manual' pertence a um ERP externo — o ERP é dono,
a API é somente leitura para ela. origem='manual' continua totalmente
editável (farmácia sem ERP, nosso Postgres é a fonte da verdade legítima).
"""

from typing import Protocol

from fastapi import HTTPException, status


class _TemOrigem(Protocol):
    origem: str


def exigir_origem_editavel(obj: _TemOrigem) -> None:
    if obj.origem != "manual":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Este registro é gerenciado pelo ERP '{obj.origem}' e é somente leitura por aqui — "
                "a alteração precisa ser feita no ERP de origem."
            ),
        )
