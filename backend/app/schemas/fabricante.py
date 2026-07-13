import uuid

from pydantic import BaseModel, ConfigDict


class FabricanteBase(BaseModel):
    nome: str
    cnpj: str | None = None
    registro_anvisa: str | None = None
    pais_origem: str = "Brasil"
    ativo: bool = True


class FabricanteCreate(FabricanteBase):
    pass


class FabricanteUpdate(BaseModel):
    nome: str | None = None
    cnpj: str | None = None
    registro_anvisa: str | None = None
    pais_origem: str | None = None
    ativo: bool | None = None


class FabricanteRead(FabricanteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
