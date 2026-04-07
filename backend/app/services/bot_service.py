"""
Bot Service — orchestrator for incoming WhatsApp messages.

This is the central orchestrator that ties together:
  1. User lookup / auto-creation  (usuario_service)
  2. LLM financial extraction     (llm_service)
  3. Movement persistence         (movimiento_service)
  4. Dynamic balance calculation   (movimiento_service)
  5. JWT generation for dashboard  (core/security)
  6. WhatsApp response delivery    (whatsapp_service)

This function runs as a BackgroundTask, so it manages its own DB session.
"""

import logging

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.services.llm_service import extract_financial_data
from app.services.movimiento_service import calcular_saldo, crear_movimiento
from app.services.usuario_service import get_or_create_usuario
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)


async def process_incoming_message(phone: str, text: str) -> None:
    """
    Full orchestration flow for an incoming WhatsApp message.

    Runs as a background task — manages its own DB session and
    never raises exceptions to the caller.

    Parameters
    ----------
    phone : str
        The sender's phone number (international format).
    text : str
        The raw text message from the user.
    """
    logger.info("Processing message from=%s text=%s", phone, text[:80])

    try:
        async with AsyncSessionLocal() as db:
            # ── 1. Get or create user ──────────────────────────────
            user = await get_or_create_usuario(phone, db)
            logger.info("User resolved: id=%d phone=%s", user.id, phone)

            # ── 2. Extract financial data via LLM ──────────────────
            llm_result = await extract_financial_data(text)
            logger.info(
                "LLM result: tipo=%s monto=%s cat=%s provider=%s",
                llm_result.get("tipo"),
                llm_result.get("monto"),
                llm_result.get("categoria"),
                llm_result.get("proveedor_usado"),
            )

            tipo = llm_result.get("tipo", "EGRESO")
            monto = float(llm_result.get("monto", 0))
            categoria = llm_result.get("categoria", "Otros")
            nota = llm_result.get("nota", "")

            # ── 3. Persist movement (only INGRESO / EGRESO) ────────
            if tipo in ("INGRESO", "EGRESO") and monto > 0:
                await crear_movimiento(
                    usuario_id=user.id,
                    tipo=tipo,
                    monto=monto,
                    categoria=categoria,
                    nota=nota,
                    db=db,
                )

            # ── 4. Calculate dynamic balance ───────────────────────
            saldo_data = await calcular_saldo(user.id, db)
            saldo = saldo_data["saldo"]

            # ── 5. Generate temporary JWT for dashboard access ─────
            token = create_access_token(data={"sub": str(user.id)})

            # ── 6. Compose and send WhatsApp response ──────────────
            if tipo == "CONSULTA":
                mensaje = (
                    f"💰 Tu saldo actual es: ${saldo:,.2f}\n"
                    f"📈 Ingresos totales: ${saldo_data['ingresos_total']:,.2f}\n"
                    f"📉 Egresos totales: ${saldo_data['egresos_total']:,.2f}\n"
                    f"\n🔗 Tu panel: https://fastrecord.app/login?token={token}"
                )
            else:
                tipo_label = "ingreso" if tipo == "INGRESO" else "gasto"
                mensaje = (
                    f"✅ Registrado. Tu {tipo_label} de ${monto:,.2f} "
                    f"en '{categoria}' fue guardado.\n"
                    f"💰 Saldo: ${saldo:,.2f}\n"
                    f"\n🔗 Tu panel: https://fastrecord.app/login?token={token}"
                )

            await send_whatsapp_message(phone, mensaje)
            logger.info("Bot flow completed for phone=%s", phone)

    except Exception as exc:
        # Background tasks must NEVER crash silently without logging
        logger.error(
            "Bot flow FAILED for phone=%s: %s",
            phone,
            str(exc),
            exc_info=True,
        )
