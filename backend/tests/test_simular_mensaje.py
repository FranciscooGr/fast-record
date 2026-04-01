"""
TDD — tests for POST /api/test/simular-mensaje and GET /api/v1/usuarios.

These tests mock the Groq SDK and DB services so we never hit real
external resources during CI.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ─────────────────────────────────────────────────────
_FAKE_USER = MagicMock(id=1, nombre="Usuario", apellido="WhatsApp",
                       telefono="+5491122334455", moneda_principal="ARS")

_FAKE_SALDO = {
    "ingresos_total": 50000.00,
    "egresos_total": 1500.00,
    "saldo": 48500.00,
}

_FAKE_MOVEMENT = MagicMock(id=1)


def _patch_db_services(
    llm_return: dict,
    saldo: dict | None = None,
    user: MagicMock | None = None,
):
    """Convenience context manager to mock all DB-touching services."""
    return (
        patch(
            "app.api.v1.endpoints.simulador.extract_financial_data",
            new_callable=AsyncMock,
            return_value=llm_return,
        ),
        patch(
            "app.api.v1.endpoints.simulador.get_or_create_usuario",
            new_callable=AsyncMock,
            return_value=user or _FAKE_USER,
        ),
        patch(
            "app.api.v1.endpoints.simulador.crear_movimiento",
            new_callable=AsyncMock,
            return_value=_FAKE_MOVEMENT,
        ),
        patch(
            "app.api.v1.endpoints.simulador.calcular_saldo",
            new_callable=AsyncMock,
            return_value=saldo or _FAKE_SALDO,
        ),
    )


# ────────────────────────────────────────────────────────────────
# 1. Happy-path: Groq returns EGRESO → 200
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_simular_mensaje_ok(client):
    """When Groq returns a well-formed EGRESO JSON, the endpoint should
    return 200 with the parsed financial data, confirmation, and saldo."""

    fake_llm = {
        "tipo": "EGRESO",
        "monto": 1500.00,
        "categoria": "Comida",
        "nota": "Pizza con amigos",
    }

    p1, p2, p3, p4 = _patch_db_services(fake_llm)
    with p1, p2, p3, p4:
        response = await client.post(
            "/api/v1/test/simular-mensaje",
            json={
                "telefono": "+5491122334455",
                "texto_mensaje": "Pagué 1500 de pizza con amigos",
            },
        )

    assert response.status_code == 200
    data = response.json()

    assert data["ok"] is True
    assert data["datos_parseados"]["tipo"] == "EGRESO"
    assert data["datos_parseados"]["monto"] == 1500.00
    assert data["datos_parseados"]["categoria"] == "Comida"
    assert data["datos_parseados"]["nota"] == "Pizza con amigos"
    assert "mensaje_usuario" in data
    assert "saldo_actual" in data
    assert data["saldo_actual"]["saldo"] == 48500.00


# ────────────────────────────────────────────────────────────────
# 2. Validation: missing required fields → 422
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_simular_mensaje_missing_fields(client):
    """Sending a body without 'texto_mensaje' must return 422."""

    response = await client.post(
        "/api/v1/test/simular-mensaje",
        json={"telefono": "+5491122334455"},
    )

    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────
# 3. Validation: empty texto_mensaje → 422
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_simular_mensaje_empty_text(client):
    """An empty string for 'texto_mensaje' must be rejected."""

    response = await client.post(
        "/api/v1/test/simular-mensaje",
        json={"telefono": "+5491122334455", "texto_mensaje": ""},
    )

    assert response.status_code == 422


# ────────────────────────────────────────────────────────────────
# 4. LLM failure: Groq raises → 502
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_simular_mensaje_llm_failure(client):
    """If the LLM service raises, the endpoint must return 502."""

    with patch(
        "app.api.v1.endpoints.simulador.extract_financial_data",
        new_callable=AsyncMock,
        side_effect=Exception("Groq API timeout"),
    ):
        response = await client.post(
            "/api/v1/test/simular-mensaje",
            json={
                "telefono": "+5491122334455",
                "texto_mensaje": "Pagué 1500 de pizza",
            },
        )

    assert response.status_code == 502
    data = response.json()
    assert "detail" in data # Verifica que exista el mensaje de error de FastAPI


# ────────────────────────────────────────────────────────────────
# 5. INGRESO variant
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_simular_mensaje_ingreso(client):
    """Validate the happy-path for an INGRESO message."""

    fake_llm = {
        "tipo": "INGRESO",
        "monto": 50000.00,
        "categoria": "Sueldo",
        "nota": "Cobro del mes de marzo",
    }

    saldo = {"ingresos_total": 50000.00, "egresos_total": 0.0, "saldo": 50000.00}
    p1, p2, p3, p4 = _patch_db_services(fake_llm, saldo=saldo)
    with p1, p2, p3, p4:
        response = await client.post(
            "/api/v1/test/simular-mensaje",
            json={
                "telefono": "+5491155667788",
                "texto_mensaje": "Me pagaron 50000 del sueldo de marzo",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["datos_parseados"]["tipo"] == "INGRESO"
    assert data["datos_parseados"]["monto"] == 50000.00
    assert data["saldo_actual"]["saldo"] == 50000.00


# ════════════════════════════════════════════════════════════════
# NEW TESTS
# ════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────
# 6. ESTABLECER_FONDO: "mi fondo es 90000" → INGRESO + Fondo inicial
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_establecer_fondo(client):
    """When the user sets an initial fund, the LLM should return
    tipo=INGRESO, categoria='Fondo inicial', and the movement should
    be persisted."""

    fake_llm = {
        "tipo": "INGRESO",
        "monto": 90000.00,
        "categoria": "Fondo inicial",
        "nota": "Fondo de 90000",
    }

    saldo = {"ingresos_total": 90000.00, "egresos_total": 0.0, "saldo": 90000.00}
    p1, p2, p3, p4 = _patch_db_services(fake_llm, saldo=saldo)
    with p1, p2, p3 as mock_crear, p4:
        response = await client.post(
            "/api/v1/test/simular-mensaje",
            json={
                "telefono": "+5491122334455",
                "texto_mensaje": "mi fondo es 90000",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["datos_parseados"]["tipo"] == "INGRESO"
    assert data["datos_parseados"]["categoria"] == "Fondo inicial"
    assert data["datos_parseados"]["monto"] == 90000.00
    assert data["saldo_actual"]["saldo"] == 90000.00
    # Movement WAS created (not a CONSULTA)
    mock_crear.assert_called_once()


# ────────────────────────────────────────────────────────────────
# 7. CONSULTAR_SALDO: "cuánto tengo" → CONSULTA, no movement created
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_consultar_saldo(client):
    """When the user asks for their balance, the LLM should return
    tipo=CONSULTA. No movement is created, only saldo is returned."""

    fake_llm = {
        "tipo": "CONSULTA",
        "monto": 0,
        "categoria": "saldo",
        "nota": "consulta_saldo",
    }

    saldo = {"ingresos_total": 90000.00, "egresos_total": 5000.00, "saldo": 85000.00}
    p1, p2, p3, p4 = _patch_db_services(fake_llm, saldo=saldo)
    with p1, p2, p3 as mock_crear, p4:
        response = await client.post(
            "/api/v1/test/simular-mensaje",
            json={
                "telefono": "+5491122334455",
                "texto_mensaje": "cuánto tengo",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["datos_parseados"]["tipo"] == "CONSULTA"
    assert data["datos_parseados"]["monto"] == 0
    assert data["saldo_actual"]["saldo"] == 85000.00
    # Movement should NOT have been created
    mock_crear.assert_not_called()


# ────────────────────────────────────────────────────────────────
# 8. GET /api/v1/usuarios/{telefono} → returns user
# ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_usuario_por_telefono(client):
    """GET endpoint should return the user for a given phone number."""

    fake_user = MagicMock()
    fake_user.id = 42
    fake_user.nombre = "Usuario"
    fake_user.apellido = "WhatsApp"
    fake_user.telefono = "+5491122334455"
    fake_user.moneda_principal = "ARS"

    with patch(
        "app.api.v1.endpoints.usuarios.get_or_create_usuario",
        new_callable=AsyncMock,
        return_value=fake_user,
    ):
        response = await client.get("/api/v1/usuarios/+5491122334455")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["telefono"] == "+5491122334455"
    assert data["nombre"] == "Usuario"
    assert data["moneda_principal"] == "ARS"
