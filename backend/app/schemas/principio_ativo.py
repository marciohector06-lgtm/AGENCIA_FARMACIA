import uuid

from pydantic import BaseModel, ConfigDict


class PrincipioAtivoBase(BaseModel):
    nome: str
    nome_dcb: str | None = None
    classe_terapeutica: str
    mecanismo_acao: str | None = None
    contraindicacoes_gerais: str | None = None


class PrincipioAtivoCreate(PrincipioAtivoBase):
    pass


class PrincipioAtivoUpdate(BaseModel):
    nome: str | None = None
    nome_dcb: str | None = None
    classe_terapeutica: str | None = None
    mecanismo_acao: str | None = None
    contraindicacoes_gerais: str | None = None


class PrincipioAtivoRead(PrincipioAtivoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
