"""
Document Service — extract text from PDF and image payment receipts.

- PDF:   uses pdfplumber to parse bytes in memory.
- Image: uses Pillow + pytesseract (Tesseract OCR) for text recognition.

Both functions return clean text suitable for the NLP pipeline.
"""

import io
import logging
import re

import pdfplumber
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


# ─── PDF extraction ─────────────────────────────────────────────


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract all text content from a PDF file loaded as bytes.

    Parameters
    ----------
    pdf_bytes : bytes
        Raw bytes of the PDF file.

    Returns
    -------
    str
        Cleaned text extracted from all pages, with excessive
        whitespace collapsed into single newlines.

    Raises
    ------
    ValueError
        If the PDF contains no extractable text.
    Exception
        Re-raises any pdfplumber parsing errors after logging.
    """
    try:
        pages_text: list[str] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            logger.info(
                "PDF opened: %d page(s), metadata=%s",
                len(pdf.pages),
                pdf.metadata,
            )

            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
                    logger.debug(
                        "Page %d: extracted %d chars", i + 1, len(text)
                    )
                else:
                    logger.debug("Page %d: no extractable text", i + 1)

        if not pages_text:
            logger.warning("PDF has no extractable text (possibly a scan)")
            raise ValueError(
                "El PDF no contiene texto extraíble. "
                "Puede ser un documento escaneado."
            )

        # ── Clean up: collapse multiple blank lines ──────────────
        raw_text = "\n".join(pages_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()

        logger.info(
            "PDF text extraction complete: %d chars from %d page(s)",
            len(clean_text),
            len(pages_text),
        )
        return clean_text

    except ValueError:
        raise  # re-raise our own ValueError

    except Exception as exc:
        logger.error(
            "Failed to extract text from PDF: %s",
            str(exc),
            exc_info=True,
        )
        raise


# ─── Image OCR extraction ───────────────────────────────────────


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Extract text from an image via Tesseract OCR.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes of the image file (JPEG, PNG, WEBP, etc.).

    Returns
    -------
    str
        Cleaned text recognised from the image.

    Raises
    ------
    ValueError
        If no recognisable text is found in the image.
    Exception
        Re-raises PIL / Tesseract errors after logging.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        logger.info(
            "Image opened for OCR: format=%s size=%s mode=%s",
            image.format,
            image.size,
            image.mode,
        )

        # Use Spanish language pack for better accuracy with AR receipts
        text = pytesseract.image_to_string(image, lang="spa")

        clean = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not clean:
            logger.warning("OCR produced no text from image")
            raise ValueError(
                "La imagen no contiene texto reconocible."
            )

        logger.info(
            "Image OCR complete: %d chars extracted",
            len(clean),
        )
        return clean

    except ValueError:
        raise  # re-raise our own ValueError

    except Exception as exc:
        logger.error(
            "Failed to extract text from image: %s",
            str(exc),
            exc_info=True,
        )
        raise
