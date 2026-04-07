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
        "Extracts the phone number and text from the first message, "
        "ignoring status/read notifications. Delegates processing "
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
                    # Only process text messages
                    if message.get("type") != "text":
                        logger.debug(
                            "Skipping non-text message type=%s",
                            message.get("type"),
                        )
                        continue

                    phone = message.get("from", "")
                    text = message.get("text", {}).get("body", "")

                    # --- PARCHE ARGENTINA: Quitar el 9 después del 54 ---
                    if phone.startswith("549") and len(phone) == 13:
                        logger.info("Aplicando parche AR: limpiando el 9 del número %s", phone)
                        phone = "54" + phone[3:]
                    # ----------------------------------------------------

                    if not phone or not text:
                        logger.warning(
                            "Message with empty phone or text — skipping"
                        )
                        continue

                    logger.info(
                        "Queueing message processing: from=%s text=%s",
                        phone,
                        text[:80],
                    )

                    background_tasks.add_task(
                        process_incoming_message,
                        phone,
                        text,
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