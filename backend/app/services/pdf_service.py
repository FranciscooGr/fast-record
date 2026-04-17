"""
PDF Service — extract text content from PDF payment receipts.

Uses pdfplumber to parse PDF bytes in memory (no disk I/O required).
Designed to process WhatsApp-forwarded payment receipts
(e.g. Mercado Pago transfers) and return clean text suitable
for the NLP pipeline.
"""

import io
import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)


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
