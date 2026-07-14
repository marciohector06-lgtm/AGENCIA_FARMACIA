"""FASE 1 (SEC-07): teto comum pra paginação. Sem isso, GET /clientes?limit=999999
despeja a tabela inteira (CPFs incluídos) numa authenticated request qualquer."""

from typing import Annotated

from fastapi import Query

LimitQuery = Annotated[int, Query(ge=1, le=100)]
SkipQuery = Annotated[int, Query(ge=0)]
