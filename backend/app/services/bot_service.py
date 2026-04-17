"""
Bot Service — orchestrator for incoming WhatsApp messages.

This is the central orchestrator that ties together:
  1. User lookup / auto-creation  (usuario_service)
  2. PDF receipt extraction        (pdf_service + whatsapp_service)
  3. Local NLP extraction          (hybrid_nlp_service — 100 % regex)
  4. Movement persistence         (movimiento_service)
  5. Dynamic balance calculation   (movimiento_service)
  6. WhatsApp response delivery    (whatsapp_service)

This function runs as a BackgroundTask, so it manages its own DB session.
"""

import logging

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.hybrid_nlp_service import analyze_hybrid_message
from app.services.movimiento_service import calcular_saldo, crear_movimiento
from app.services.pdf_service import extract_text_from_pdf_bytes
from app.services.usuario_service import get_or_create_usuario
from app.services.whatsapp_service import (
    download_whatsapp_media,
    send_whatsapp_message,
)

logger = logging.getLogger(__name__)

# ── Onboarding / help message ──────────────────────────────────
MSG_AYUDA = (
    "🤖 ¡Hola! Soy FastRecord.\n\n"
    "Para registrar un movimiento o consultar saldo, usá este formato:\n"
    "?: Saldo\n"
    "🟢 Ingresos: 'cobré 10000 de sueldo'\n"
    "🔴 Gastos: 'pague 2000 en comida'\n"
    "📄 También podés enviarme un comprobante de pago en PDF.\n\n"
    "¡Escribime tu primer movimiento!"
)

# ── PDF-specific error message ─────────────────────────────────
MSG_PDF_NO_ENTENDIDO = (
    "❌ Uy, no pude extraer los datos de este PDF.\n"
    "Por ahora solo entiendo comprobantes de transferencia "
    "de Mercado Pago.\n\n"
    "Si querés, escribí el monto manualmente:\n"
    "Ej: 'pagué 18000 en cine'"
)


async def process_incoming_message(
    phone: str,
    text: str,
    media_id: str | None = None,
) -> None:
    """
    Full orchestration flow for an incoming WhatsApp message.

    Runs as a background task — manages its own DB session and
    never raises exceptions to the caller.

    Parameters
    ----------
    phone : str
        The sender's phone number (international format).
    text : str
        The raw text message from the user. Empty string when
        the message is a document/PDF.
    media_id : str | None
        If present, the Meta media ID for a PDF document
        that needs to be downloaded and OCR'd.
    """
    logger.info(
        "Processing message from=%s text=%s media_id=%s",
        phone,
        text[:80] if text else "(pdf)",
        media_id or "N/A",
    )

    try:
        async with AsyncSessionLocal() as db:
            # ── 1. Get or create user ──────────────────────────────
            user, is_new = await get_or_create_usuario(phone, db)
            logger.info(
                "User resolved: id=%d phone=%s is_new=%s",
                user.id,
                phone,
                is_new,
            )

            # ── 1b. Onboarding: greet new users and stop ───────────
            if is_new:
                await send_whatsapp_message(phone, MSG_AYUDA)
                logger.info("Onboarding message sent to new user phone=%s", phone)
                return

            # ── 2. Resolve texto_usuario from text or PDF ──────────
            texto_usuario: str = text
            es_documento: bool = bool(media_id)

            if media_id:
                # ── 2a. PDF document path ──────────────────────────
                await send_whatsapp_message(
                    phone,
                    "📄 Recibí tu comprobante, lo estoy analizando...",
                )

                try:
                    pdf_bytes = await download_whatsapp_media(media_id)
                    pdf_text = extract_text_from_pdf_bytes(pdf_bytes)
                    texto_usuario = f"Comprobante de pago: {pdf_text}"
                    logger.info(
                        "PDF processed for phone=%s: %d chars extracted",
                        phone,
                        len(pdf_text),
                    )
                except ValueError as exc:
                    # PDF with no extractable text (scan, image-based)
                    await send_whatsapp_message(
                        phone,
                        f"⚠️ No pude leer el PDF: {exc}\n"
                        "Intentá enviar el comprobante como imagen o "
                        "escribí el monto manualmente.",
                    )
                    logger.warning(
                        "PDF text extraction failed for phone=%s: %s",
                        phone,
                        str(exc),
                    )
                    return
                except Exception as exc:
                    await send_whatsapp_message(
                        phone,
                        "❌ Hubo un error al procesar tu comprobante. "
                        "Por favor, intentá de nuevo o escribí el monto "
                        "manualmente.",
                    )
                    logger.error(
                        "PDF processing FAILED for phone=%s media_id=%s: %s",
                        phone,
                        media_id,
                        str(exc),
                        exc_info=True,
                    )
                    return

            # Guard: if we still have no text (shouldn't happen)
            if not texto_usuario:
                logger.warning(
                    "No text to process for phone=%s — skipping", phone
                )
                return

            # ── 3. Extract financial data (100 % local regex) ───────
            llm_result = await analyze_hybrid_message(texto_usuario)
            logger.info(
                "NLP result: tipo=%s monto=%s cat=%s provider=%s",
                llm_result.get("tipo"),
                llm_result.get("monto"),
                llm_result.get("categoria"),
                llm_result.get("proveedor_usado"),
            )

            # ── 3b. Guard: reject unrecognised formats ──────────────
            if llm_result["tipo"] == "DESCONOCIDO":
                logger.warning(
                    "Mensaje no reconocido de phone=%s es_documento=%s: '%s'",
                    phone,
                    es_documento,
                    texto_usuario[:80],
                )
                if es_documento:
                    # UX: PDF-specific error — don't show generic onboarding
                    await send_whatsapp_message(phone, MSG_PDF_NO_ENTENDIDO)
                else:
                    await send_whatsapp_message(phone, MSG_AYUDA)
                return

            tipo = llm_result.get("tipo", "EGRESO")
            monto = float(llm_result.get("monto", 0))
            categoria = llm_result.get("categoria", "Otros")
            nota = llm_result.get("nota", "")

            # ── 4. Persist movement (only INGRESO / EGRESO) ────────
            if tipo in ("INGRESO", "EGRESO") and monto > 0:
                await crear_movimiento(
                    usuario_id=user.id,
                    tipo=tipo,
                    monto=monto,
                    categoria=categoria,
                    nota=nota,
                    db=db,
                )

            # ── 5. Calculate dynamic balance ───────────────────────
            saldo_data = await calcular_saldo(user.id, db)
            saldo = saldo_data["saldo"]

            # ── 6. Build clean dashboard URL with public_id ────────
            frontend_url = f"{settings.FRONTEND_URL}/d/{user.public_id}"

            # ── 7. Compose and send WhatsApp response ──────────────
            if tipo == "CONSULTA":
                mensaje = (
                    f"💰 Tu saldo actual es: ${saldo:,.2f}\n"
                    f"📈 Ingresos totales: ${saldo_data['ingresos_total']:,.2f}\n"
                    f"📉 Egresos totales: ${saldo_data['egresos_total']:,.2f}\n"
                    f"\n🔗 Tu panel: {frontend_url}"
                )
            else:
                tipo_label = "ingreso" if tipo == "INGRESO" else "gasto"
                source_label = " (desde comprobante)" if media_id else ""
                mensaje = (
                    f"✅ Registrado{source_label}. Tu {tipo_label} de ${monto:,.2f} "
                    f"en '{categoria}' fue guardado.\n"
                    f"💰 Saldo: ${saldo:,.2f}\n"
                    f"\n🔗 Tu panel: {frontend_url}"
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
