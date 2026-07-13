import os
import uuid

import pytest
from httpx import AsyncClient

requires_db = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL não configurada"
)


@requires_db
async def test_criar_e_consultar_produto(client: AsyncClient) -> None:
    principio_payload = {
        "nome": f"Principio Teste {uuid.uuid4().hex[:8]}",
        "classe_terapeutica": "Analgesico",
    }
    principio_resp = await client.post("/api/v1/principios-ativos", json=principio_payload)
    assert principio_resp.status_code == 201
    principio_id = principio_resp.json()["id"]

    fabricante_payload = {"nome": f"Fabricante Teste {uuid.uuid4().hex[:8]}"}
    fabricante_resp = await client.post("/api/v1/fabricantes", json=fabricante_payload)
    assert fabricante_resp.status_code == 201
    fabricante_id = fabricante_resp.json()["id"]

    produto_payload = {
        "principio_ativo_id": principio_id,
        "fabricante_id": fabricante_id,
        "nome_comercial": "Analgesico Teste 500mg",
        "forma_farmaceutica": "comprimido",
        "via_administracao": "oral",
        "concentracao_valor": "500.000",
        "concentracao_unidade": "mg",
        "quantidade_embalagem": 20,
        "tarja": "isento",
        "preco_tabela": "12.90",
    }
    produto_resp = await client.post("/api/v1/produtos", json=produto_payload)
    assert produto_resp.status_code == 201
    produto_id = produto_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/produtos/{produto_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["nome_comercial"] == "Analgesico Teste 500mg"

    patch_resp = await client.patch(f"/api/v1/produtos/{produto_id}", json={"preco_tabela": "13.50"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["preco_tabela"] == "13.50"


@requires_db
async def test_produto_medicamento_sem_principio_ativo_falha(client: AsyncClient) -> None:
    fabricante_payload = {"nome": f"Fabricante Teste {uuid.uuid4().hex[:8]}"}
    fabricante_resp = await client.post("/api/v1/fabricantes", json=fabricante_payload)
    fabricante_id = fabricante_resp.json()["id"]

    produto_payload = {
        "fabricante_id": fabricante_id,
        "nome_comercial": "Comprimido Sem Principio Ativo",
        "forma_farmaceutica": "comprimido",
        "via_administracao": "oral",
        "concentracao_valor": "500.000",
        "concentracao_unidade": "mg",
        "quantidade_embalagem": 20,
        "tarja": "isento",
        "preco_tabela": "12.90",
    }
    produto_resp = await client.post("/api/v1/produtos", json=produto_payload)
    assert produto_resp.status_code == 409
