"""
Simulator endpoint — POST /api/test/simular-mensaje

Allows developers to test the full LLM → DB flow without hitting
the real WhatsApp API.  This router is intended for development only.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.schemas.simulacion import (
    DatosFinancieros,
    MensajeSimulado,
    SaldoActual,
    SimulacionErrorResponse,
    SimulacionResponse,
)
from app.services.llm_service import extract_financial_data
from app.services.movimiento_service import calcular_saldo, crear_movimiento
from app.services.usuario_service import get_or_create_usuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["simulador"])


@router.post(
    "/simular-mensaje",
    response_model=SimulacionResponse,
    responses={502: {"model": SimulacionErrorResponse}},
    summary="Simulate a WhatsApp message — full LLM + DB flow",
    description=(
        "Receives a simulated message, sends it to Groq, persists the "
        "movement in the DB, and returns the parsed data + computed balance."
    ),
)
async def simular_mensaje(
    body: MensajeSimulado,
    db: AsyncSession = Depends(get_db),
):
    """
    Full flow:
    1. Receive the Pydantic-validated body.
    2. Send texto_mensaje to Groq via llm_service.
    3. Validate the LLM response as DatosFinancieros.
    4. Get or create the user by phone number.
    5. If INGRESO or EGRESO → persist the movement.
    6. If CONSULTA → skip persistence.
    7. Calculate the running balance (saldo) dynamically.
    8. Return parsed data + confirmation message + saldo.
    """
    # ── Step 1: LLM extraction ──────────────────────────────────
    try:
        raw_data = await extract_financial_data(body.texto_mensaje)
    except Exception as exc:
        logger.error(
            "LLM extraction failed for phone=%s: %s",
            body.telefono,
            str(exc),
        )
        raise HTTPException(
            status_code=502,
            detail={"ok": False, "error": f"Error al procesar con LLM: {exc}"},
        )

    # ── Step 2: Pydantic validation ─────────────────────────────
    datos = DatosFinancieros(**raw_data)

    # ── Step 3: Get or create user ──────────────────────────────
    user = await get_or_create_usuario(body.telefono, db)

    # ── Step 4: Persist movement (only INGRESO / EGRESO) ────────
    if datos.tipo in ("INGRESO", "EGRESO"):
        await crear_movimiento(
            usuario_id=user.id,
            tipo=datos.tipo,
            monto=datos.monto,
            categoria=datos.categoria,
            nota=datos.nota,
            db=db,
        )

    # ── Step 5: Calculate balance (always) ──────────────────────
    saldo_dict = await calcular_saldo(user.id, db)

    # ── Step 6: Build confirmation message ──────────────────────
    if datos.tipo == "CONSULTA":
        mensaje_usuario = (
            f"💰 Tu saldo actual es: ${saldo_dict['saldo']:,.2f}\n"
            f"📈 Ingresos totales: ${saldo_dict['ingresos_total']:,.2f}\n"
            f"📉 Egresos totales: ${saldo_dict['egresos_total']:,.2f}"
        )
    else:
        tipo_label = "ingreso" if datos.tipo == "INGRESO" else "gasto"
        mensaje_usuario = (
            f"✅ Registré tu {tipo_label} de ${datos.monto:,.2f} "
            f"en la categoría '{datos.categoria}'.\n"
            f"📝 Nota: {datos.nota}\n"
            f"💰 Saldo actual: ${saldo_dict['saldo']:,.2f}"
        )

    return SimulacionResponse(
        ok=True,
        datos_parseados=datos,
        mensaje_usuario=mensaje_usuario,
        saldo_actual=SaldoActual(**saldo_dict),
    )
