"""
WhatsApp Webhook endpoints.

GET  /webhook — Meta verification handshake.
POST /webhook — Incoming message receiver (delegates to bot_service
               via BackgroundTasks for immediate 200 OK response).
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import PlainTextResponse, Response

from app.core.config import settings
from app.services.bot_service import process_incoming_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get(
    "",
    summary="Meta webhook verification",
    description=(
        "Handles the GET verification request from Meta. "
        "Compares hub.verify_token with the configured WHATSAPP_VERIFY_TOKEN "
        "and returns hub.challenge in plain text."
    ),
)
async def verify_webhook(
    request: Request,
) -> Response:
    """
    Meta sends:
      GET /webhook?hub.mode=subscribe
                  &hub.verify_token=<token>
                  &hub.challenge=<challenge>

    We validate the token and return the challenge as plain text.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification succeeded")
        return PlainTextResponse(content=challenge, status_code=200)

    logger.warning(
        "Webhook verification FAILED: mode=%s token_match=%s",
        mode,
        token == settings.WHATSAPP_VERIFY_TOKEN,
    )
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post(
    "",
    summary="Receive WhatsApp messages",
    description=(
        "Receives the incoming webhook payload from Meta. "
        "Extracts the phone number and content from the first message, "
        "supporting both text and PDF document types. "
        "Ignoring status/read notifications. Delegates processing "
        "to bot_service as a background task and returns 200 OK immediately."
    ),
)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Meta requires a 200 OK response within 5 seconds.
    All heavy processing (LLM, DB, WhatsApp reply) happens in background.
    """
    body = await request.json()

    logger.debug("Webhook payload received: %s", str(body)[:500])

    # ── Extract messages from Meta's nested payload structure ────
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    msg_type = message.get("type")
                    phone = message.get("from", "")

                    # --- PARCHE ARGENTINA: Quitar el 9 después del 54 ---
                    if phone.startswith("549") and len(phone) == 13:
                        logger.info(
                            "Aplicando parche AR: limpiando el 9 del número %s",
                            phone,
                        )
                        phone = "54" + phone[3:]
                    # ----------------------------------------------------

                    text = ""
                    media_id: str | None = None

                    # ── Text messages ───────────────────────────
                    if msg_type == "text":
                        text = message.get("text", {}).get("body", "")

                    # ── Document messages (PDF receipts) ────────
                    elif msg_type == "document":
                        doc = message.get("document", {})
                        mime_type = doc.get("mime_type", "")

                        if mime_type != "application/pdf":
                            logger.debug(
                                "Skipping non-PDF document: mime_type=%s",
                                mime_type,
                            )
                            continue

                        media_id = doc.get("id", "")
                        if not media_id:
                            logger.warning(
                                "PDF document without media_id — skipping"
                            )
                            continue

                        logger.info(
                            "PDF document received: media_id=%s from=%s",
                            media_id,
                            phone,
                        )

                    else:
                        logger.debug(
                            "Skipping unsupported message type=%s",
                            msg_type,
                        )
                        continue

                    if not phone or (not text and not media_id):
                        logger.warning(
                            "Message with empty phone or content — skipping"
                        )
                        continue

                    logger.info(
                        "Queueing message processing: from=%s type=%s "
                        "text=%s media_id=%s",
                        phone,
                        msg_type,
                        text[:80] if text else "(pdf)",
                        media_id or "N/A",
                    )

                    background_tasks.add_task(
                        process_incoming_message,
                        phone,
                        text,
                        media_id,
                    )

    except Exception as exc:
        # Log but don't fail — Meta still needs the 200
        logger.error(
            "Error parsing webhook payload: %s",
            str(exc),
            exc_info=True,
        )

    # Always return 200 to Meta — no exceptions
    return {"status": "ok"}