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


async def download_whatsapp_media(media_id: str) -> bytes:
    """
    Download a media file from WhatsApp via the Meta Graph API.

    Two-step process:
      1. GET /v17.0/{media_id} → obtain the temporary download URL.
      2. GET {download_url}    → fetch the raw file bytes.

    Parameters
    ----------
    media_id : str
        The media ID provided by Meta in the incoming webhook payload.

    Returns
    -------
    bytes
        The raw file content.

    Raises
    ------
    httpx.HTTPStatusError
        If either HTTP request returns a non-2xx status.
    httpx.RequestError
        If a network-level error occurs.
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ── Step 1: Get the download URL from Meta ──────────────
        meta_url = f"https://graph.facebook.com/v17.0/{media_id}"
        logger.info("Fetching media metadata: media_id=%s", media_id)

        try:
            resp_meta = await client.get(meta_url, headers=headers)
            resp_meta.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Meta media metadata HTTP error: status=%d body=%s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Meta media metadata request error: %s", str(exc)
            )
            raise

        download_url = resp_meta.json().get("url")
        if not download_url:
            msg = f"No download URL in Meta response for media_id={media_id}"
            logger.error(msg)
            raise ValueError(msg)

        logger.info(
            "Download URL obtained for media_id=%s url=%s",
            media_id,
            download_url[:120],
        )

        # ── Step 2: Download the actual file bytes ──────────────
        try:
            resp_file = await client.get(download_url, headers=headers)
            resp_file.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Media download HTTP error: status=%d body=%s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Media download request error: %s", str(exc)
            )
            raise

        file_bytes = resp_file.content
        logger.info(
            "Media downloaded: media_id=%s size=%d bytes",
            media_id,
            len(file_bytes),
        )
        return file_bytes
