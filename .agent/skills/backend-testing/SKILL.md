---
name: backend-testing
description: Use when writing pytest tests for FastAPI endpoints, WhatsApp webhook handlers, LLM orchestration with Gemini/Groq fallback, or PostgreSQL aggregate queries. Do not use for Angular/frontend tests.
---

# Backend Testing — FastAPI + Pytest

## Use this skill when
- Escribiendo tests para endpoints REST del dashboard
- Testeando la validación de firma HMAC del webhook WhatsApp
- Verificando el comportamiento del fallback Gemini → Groq → Otros
- Validando que el saldo se calcula correctamente por agregación
- Haciendo mocks de APIs externas (WhatsApp, Gemini, Groq)

## Setup — conftest.py
```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.db.session import get_db
from app.models.base import Base

TEST_DB_URL = "postgresql+asyncpg://user:pass@localhost/fast_record_test"

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
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

## Tests del Dashboard
```python
# tests/test_dashboard.py
import pytest

@pytest.mark.asyncio
async def test_dashboard_devuelve_saldo_calculado(client, db_session):
    # Arrange — crear transacciones de prueba
    await crear_transaccion(db_session, tipo="ingreso", monto=1000)
    await crear_transaccion(db_session, tipo="gasto", monto=250)

    # Act
    response = await client.get(
        "/api/v1/dashboard/",
        headers={"Authorization": "Bearer token_valido"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["saldo"] == 750.0          # calculado, nunca de columna
    assert "gastos_por_categoria" in data  # para Chart.js

@pytest.mark.asyncio
async def test_dashboard_sin_auth_devuelve_401(client):
    response = await client.get("/api/v1/dashboard/")
    assert response.status_code == 401
```

## Tests del Webhook WhatsApp
```python
# tests/test_webhook.py
import pytest, hmac, hashlib, json
from unittest.mock import patch, AsyncMock

def firmar_payload(payload: dict, secret: str = "test_secret") -> str:
    body = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"

@pytest.mark.asyncio
async def test_webhook_rechaza_firma_invalida(client):
    response = await client.post(
        "/api/v1/webhook/whatsapp",
        json={"object": "whatsapp_business_account", "entry": []},
        headers={"X-Hub-Signature-256": "sha256=firma_falsa"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_procesa_mensaje_correctamente(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{"text": {"body": "gasté 500 en comida"}}]}}]}]
    }
    with patch("app.services.llm_orchestrator.orchestrate", new_callable=AsyncMock,
               return_value={"categoria": "Comida", "confianza": 0.92, "proveedor_usado": "gemini"}):
        response = await client.post(
            "/api/v1/webhook/whatsapp",
            json=payload,
            headers={"X-Hub-Signature-256": firmar_payload(payload)}
        )
    assert response.status_code == 200
```

## Tests del Orquestador LLM
```python
# tests/test_llm_orchestrator.py
import pytest
from unittest.mock import patch, AsyncMock
from app.services.llm_orchestrator import orchestrate

@pytest.mark.asyncio
async def test_usa_gemini_exitosamente():
    mock_response = {"categoria": "Transporte", "confianza": 0.95}
    with patch("app.services.llm_orchestrator.gemini_call",
               new_callable=AsyncMock, return_value=mock_response):
        result = await orchestrate("viaje en taxi")
    assert result["proveedor_usado"] == "gemini"
    assert result["categoria"] == "Transporte"

@pytest.mark.asyncio
async def test_fallback_a_groq_cuando_gemini_falla():
    with patch("app.services.llm_orchestrator.gemini_call",
               side_effect=TimeoutError("gemini timeout")):
        with patch("app.services.llm_orchestrator.groq_call",
                   new_callable=AsyncMock,
                   return_value={"categoria": "Comida", "confianza": 0.88}):
            result = await orchestrate("almuerzo en restaurante")
    assert result["proveedor_usado"] == "groq"

@pytest.mark.asyncio
async def test_fallback_a_otros_cuando_todos_fallan():
    with patch("app.services.llm_orchestrator.gemini_call",
               side_effect=Exception("error")):
        with patch("app.services.llm_orchestrator.groq_call",
                   side_effect=Exception("error")):
            result = await orchestrate("descripción sin categoría")
    assert result["categoria"] == "Otros"
    assert result["proveedor_usado"] == "fallback_otros"
    assert result["confianza"] == 0.0
```

## Correr los tests
```bash
# Todos los tests
pytest ./backend/tests/ -v

# Solo un módulo
pytest ./backend/tests/test_webhook.py -v

# Con cobertura
pytest ./backend/tests/ --cov=app --cov-report=term-missing
```

## Do not
- No usar la DB de producción — siempre `fast_record_test`
- No hacer llamadas reales a Gemini/Groq/WhatsApp en tests — mockear siempre
- No testear el framework de FastAPI — testear tu lógica de negocio
- No olvidar el `rollback()` en el fixture de sesión DB
