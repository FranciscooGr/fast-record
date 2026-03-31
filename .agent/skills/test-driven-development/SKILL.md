---
name: test-driven-development
description: Use when writing tests for FastAPI endpoints, webhook handlers, LLM orchestration fallback logic, or database queries. Always write the test before the implementation.
---

# Test Driven Development — Backend Master

## Use this skill when
- Implementando nuevo endpoint o servicio
- Agregando lógica de fallback LLM
- Validando la regla del saldo calculado
- Testeando el webhook de WhatsApp

## Ciclo TDD
```
1. RED   → Escribir el test que falla
2. GREEN → Escribir el mínimo código para que pase
3. REFACTOR → Limpiar sin romper el test
```

## Setup de tests
```python
# conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.db.session import get_db

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/test_db"

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

## Test de Endpoint REST
```python
# tests/test_dashboard.py
import pytest

@pytest.mark.asyncio
async def test_get_dashboard_returns_saldo_calculado(client):
    # Arrange — insertar transacciones de prueba
    # Act
    response = await client.get("/api/v1/dashboard/")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "saldo" in data
    # El saldo NUNCA viene de una columna — es calculado
    assert isinstance(data["saldo"], float)
```

## Test del Fallback LLM
```python
# tests/test_llm_orchestrator.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_usa_gemini_cuando_funciona():
    with patch("app.services.llm_orchestrator.gemini_call",
               return_value={"categoria": "Comida", "confianza": 0.95}) as mock:
        result = await orchestrate_llm("compré pizza")
    assert result["proveedor_usado"] == "gemini"
    assert result["categoria"] == "Comida"

@pytest.mark.asyncio
async def test_fallback_a_groq_cuando_gemini_falla():
    with patch("app.services.llm_orchestrator.gemini_call",
               side_effect=Exception("timeout")):
        with patch("app.services.llm_orchestrator.groq_call",
                   return_value={"categoria": "Transporte", "confianza": 0.88}):
            result = await orchestrate_llm("taxi al trabajo")
    assert result["proveedor_usado"] == "groq"

@pytest.mark.asyncio
async def test_fallback_a_otros_cuando_ambos_fallan():
    with patch("app.services.llm_orchestrator.gemini_call",
               side_effect=Exception("error")):
        with patch("app.services.llm_orchestrator.groq_call",
                   side_effect=Exception("error")):
            result = await orchestrate_llm("texto cualquiera")
    assert result["categoria"] == "Otros"
    assert result["proveedor_usado"] == "fallback_otros"
```

## Test del Webhook WhatsApp
```python
# tests/test_webhook.py
import pytest
import hmac, hashlib, json

def generar_firma(payload: dict, secret: str) -> str:
    body = json.dumps(payload).encode()
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_webhook_rechaza_firma_invalida(client):
    response = await client.post(
        "/api/v1/webhook/whatsapp",
        json={"message": "test"},
        headers={"X-Hub-Signature-256": "sha256=firma_invalida"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_acepta_firma_valida(client):
    payload = {"object": "whatsapp_business_account", "entry": []}
    firma = generar_firma(payload, "test_secret")
    response = await client.post(
        "/api/v1/webhook/whatsapp",
        json=payload,
        headers={"X-Hub-Signature-256": firma}
    )
    assert response.status_code == 200
```

## Test de la Regla del Saldo
```python
# tests/test_saldo_calculado.py
@pytest.mark.asyncio
async def test_saldo_es_suma_de_transacciones(db_session):
    # Insertar ingresos y gastos
    await insertar_transaccion(db_session, tipo="ingreso", monto=1000)
    await insertar_transaccion(db_session, tipo="gasto", monto=300)
    # El saldo debe ser calculado, nunca leído de columna
    saldo = await calcular_saldo(db_session, cuenta_id=1)
    assert saldo == 700.0
```

## Do not
- No mockear lo que no necesitás — solo dependencias externas (APIs, DB en unit tests)
- No escribir tests que testean el framework, no tu código
- No saltear el paso RED — el test debe fallar primero
- No usar la DB de producción en tests
