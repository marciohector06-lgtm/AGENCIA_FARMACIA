from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # str, não EmailStr: EmailStr exigiria a dependência extra
    # `email-validator`, e a lista de dependências novas desta fase já foi
    # combinada (python-jose, passlib, slowapi) — validação de formato de
    # e-mail não é crítica aqui, quem decide se é válido é o SELECT no banco.
    email: str = Field(min_length=1, max_length=150)
    senha: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
