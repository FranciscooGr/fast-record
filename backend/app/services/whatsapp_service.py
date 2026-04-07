"""
WhatsApp Service — send messages via the Meta Graph API.

Uses httpx.AsyncClient for non-blocking HTTP calls.
Errors are logged but NOT raised, so the bot flow is never interrupted
by a downstream delivery failure.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://graph.facebook.com/v17.0/"
    f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
)


async def send_whatsapp_message(to_number: str, text: str) -> dict | None:
    """
    Send a text message to a WhatsApp user.

    Parameters
    ----------
    to_number : str
        Recipient phone number in international format (e.g. "5491122334455").
    text : str
        The message body to send.

    Returns
    -------
    dict | None
        The JSON response from Meta on success, or None on failure.
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _BASE_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "WhatsApp message sent to=%s message_id=%s",
                to_number,
                data.get("messages", [{}])[0].get("id", "unknown"),
            )
            return data

    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp API HTTP error: status=%d body=%s",
            exc.response.status_code,
            exc.response.text[:300],
        )
    except httpx.RequestError as exc:
        logger.error(
            "WhatsApp API request error: %s",
            str(exc),
        )
    except Exception as exc:
        logger.error(
            "WhatsApp unexpected error: %s",
            str(exc),
        )

    return None
