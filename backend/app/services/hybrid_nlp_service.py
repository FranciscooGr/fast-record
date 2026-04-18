"""
Local NLP Service — 100 % Regex, zero external API calls.

All incoming messages are resolved deterministically with Python regex.
No LLM provider is used; running costs are $0.

Processing order:
  -1. Fast Path -1 — Cancel / undo keywords     → CANCELAR
   0. Fast Path 0  — Mercado Pago PDF receipts   → EGRESO (comprobante)
   1. Fast Path 1  — Balance / query keywords     → CONSULTA
   2. Fast Path 2  — <monto> <categoría>          → EGRESO
   3. Fast Path 3  — <verbo_gasto> <monto> <cat>  → EGRESO
   4. Fast Path 4  — <verbo_ingreso> <monto>      → INGRESO
   5. Default      — DESCONOCIDO (error determinista)
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Fast Path -1: Cancel / Undo intent ───────────────────────────
# Exact keywords that immediately trigger cancellation
_CANCEL_KEYWORDS: set[str] = {
    "cancela",
    "cancelar",
    "deshacer",
    "anular",
    "me equivoque",
    "me equivoqué",
}

# Phrase patterns: "borra el ultimo", "elimina el ultimo", etc.
_RE_CANCEL_PHRASE = re.compile(
    r"^(?:borra|elimina|quita|saca)(?:r?)\s+(?:el\s+)?(?:ultimo|último)$",
    re.IGNORECASE,
)

# ── Fast Path 0: Mercado Pago PDF receipt detection ──────────────
# MP PDFs produce doubled-letter artefacts: ttoottaall, ttííttuulloo
#
# STRICT monto pattern — Argentine canonical format only:
#   $ 20.000,50  |  $ 20.000  |  $ 1.200,00  |  $ 500
# Groups of 1-3 digits followed by .XXX blocks, with optional ,XX cents.
# This intentionally REJECTS flat OCR garbage like "$2000000" where
# superscript cents got flattened into the integer part.
_RE_PDF_MONTO_STRICT = re.compile(
    r"\$\s*(\d{1,3}(?:\.\d{3})*)(?:,(\d{2}))?"
)

# FALLBACK monto — loose capture for non-standard formats.
# Only used when the strict regex finds nothing.
_RE_PDF_MONTO_FALLBACK = re.compile(
    r"\$\s*([\d.,]+)"
)
# Título pattern — handles MP doubled-letter artefact and normal text
_RE_PDF_TITULO = re.compile(
    r"(?:ttííttuulloo|título|titulo)[:\s]*:?\s*([^\n]+)",
    re.IGNORECASE,
)

# ── Fast Path 1: exact-match query keywords ──────────────────────
_QUERY_KEYWORDS: set[str] = {
    "saldo",
    "resumen",
    "consulta",
    "cuanto tengo",
    "cuánto tengo",
    "cuanto me queda",
    "cuánto me queda",
    "como voy",
    "cómo voy",
}

# ── Category normalisation map (Argentine slang → canonical) ─────
_MAPEO_CATEGORIAS: dict[str, str] = {
    # Transporte
    "nafta": "Transporte",
    "ypf": "Transporte",
    "uber": "Transporte",
    "cabify": "Transporte",
    "didi": "Transporte",
    "sube": "Transporte",
    "peaje": "Transporte",
    "estacionamiento": "Transporte",
    "cochera": "Transporte",
    # Supermercado
    "super": "Supermercado",
    "supermercado": "Supermercado",
    "coto": "Supermercado",
    "carrefour": "Supermercado",
    "dia": "Supermercado",
    "chango mas": "Supermercado",
    "changomas": "Supermercado",
    "jumbo": "Supermercado",
    "vea": "Supermercado",
    # Salud
    "farmacity": "Salud",
    "farmacia": "Salud",
    "remedios": "Salud",
    "medico": "Salud",
    "médico": "Salud",
    "doctor": "Salud",
    "obra social": "Salud",
    # Salidas / Entretenimiento
    "chupi": "Salidas",
    "birra": "Salidas",
    "cerveza": "Salidas",
    "bar": "Salidas",
    "boliche": "Salidas",
    "cine": "Entretenimiento",
    "cinemark": "Entretenimiento",
    "cinemarkhoyts": "Entretenimiento",
    "hoyts": "Entretenimiento",
    "netflix": "Entretenimiento",
    "spotify": "Entretenimiento",
    # Comida
    "comida": "Comida",
    "almuerzo": "Comida",
    "cena": "Comida",
    "delivery": "Comida",
    "rappi": "Comida",
    "pedidosya": "Comida",
    # Servicios
    "luz": "Servicios",
    "gas": "Servicios",
    "agua": "Servicios",
    "internet": "Servicios",
    "wifi": "Servicios",
    "telefono": "Servicios",
    "teléfono": "Servicios",
    "celular": "Servicios",
    # Hogar
    "alquiler": "Hogar",
    "expensas": "Hogar",
    # Educación
    "universidad": "Educación",
    "facultad": "Educación",
    "curso": "Educación",
    "libro": "Educación",
    "libros": "Educación",
}

# ── Fast Path 2: <monto> <categoría> ────────────────────────────
# Examples: "5000 supermercado", "1500.50 nafta", "200,50 peaje"
_RE_MONTO_CATEGORIA = re.compile(
    r"^(\d+(?:[.,]\d{1,2})?)(?:\s+(.*))?$",
)

# ── Fast Path 3: <verbo> <monto> [en|de] <categoría> ────────────
# Root-based verb matching: prefixes catch all conjugations
# gast → gaste, gasté, gasto  |  pag → pague, pagué, pago
# compr → compre, compré       |  carg → cargué, cargue
# pus → puse, puso
_SPENDING_VERBS = r"(?:gast|pag|compr|carg|pus)[a-zñáéíóú]*"
_RE_VERBO_MONTO_CATEGORIA = re.compile(
    rf"^{_SPENDING_VERBS}\s+(\d+(?:[.,]\d{{1,2}})?)\s*(?:(?:en|de)\s+)?(.*)$",
)

# ── Fast Path 4: <verbo_ingreso> <monto> [de|por] <concepto> ─────
# cobr → cobré, cobro  |  recib → recibí, recibo
# gan → gané, gano     |  ingres → ingresé, ingreso
# sum → sumame, sumo
_INCOME_VERBS = r"(?:cobr|recib|gan|ingres|sum)[a-zñáéíóú]*"
_RE_INCOME = re.compile(
    rf"^{_INCOME_VERBS}\s+(\d+(?:[.,]\d{{1,2}})?)\s*(?:(?:de|por)\s+)?(.*)$",
)


def _parse_monto(raw: str) -> float:
    """Normalize comma-decimal to dot-decimal and parse to float."""
    return float(raw.replace(",", "."))


def _parse_monto_ar(raw: str) -> float:
    """Parse Argentine-format amount: dots as thousands, comma as decimal.

    Examples:
        "18.055,00" → 18055.00
        "1.200"     → 1200.0
        "500"       → 500.0
    """
    # Remove dots (thousands separator), replace comma with dot (decimal)
    cleaned = raw.replace(".", "").replace(",", ".")
    return float(cleaned)


def _parse_receipt_monto(match: re.Match) -> float:
    """Parse a structured Argentine amount from the strict receipt regex.

    Group 1: integer part with dots as thousands (e.g. "20.000")
    Group 2: optional 2-digit cents after comma  (e.g. "50")

    Examples:
        match("$ 20.000")    → 20000.00
        match("$ 18.055,50") → 18055.50
        match("$ 500")       → 500.00
    """
    integer_part = match.group(1).replace(".", "")  # "20.000" → "20000"
    cents = match.group(2) or "00"                   # "50" or default "00"
    return float(f"{integer_part}.{cents}")


def _normalizar_categoria(cat_raw: str | None) -> str:
    """Resolve a raw capture group into a canonical category.

    1. If None or blank → "Otros"
    2. Lookup in _MAPEO_CATEGORIAS (lowercase) → canonical value
    3. Fallback → capitalize the raw input
    """
    if not cat_raw or not cat_raw.strip():
        return "Otros"
    cat_limpia = cat_raw.strip().lower()
    return _MAPEO_CATEGORIAS.get(cat_limpia, cat_limpia.capitalize())


def _normalizar_categoria_ingreso(cat_raw: str | None) -> str:
    """Resolve income category — defaults to 'Ingreso' instead of 'Otros'."""
    if not cat_raw or not cat_raw.strip():
        return "Ingreso"
    return cat_raw.strip().capitalize()


def _build_result(
    *,
    tipo: str,
    monto: float = 0.0,
    categoria: str = "saldo",
    nota: str = "",
    proveedor_usado: str = "regex_local",
    confianza: float = 1.0,
) -> dict:
    """Return a dict that matches the contract of extract_financial_data."""
    return {
        "tipo": tipo,
        "monto": monto,
        "categoria": categoria,
        "nota": nota,
        "proveedor_usado": proveedor_usado,
        "confianza": confianza,
    }


def _try_parse_pdf_receipt(cleaned: str) -> dict | None:
    """Try to parse a Mercado Pago PDF/image receipt from cleaned text.

    Uses a two-pass strategy for amount extraction:
      1. STRICT regex — only matches canonical Argentine format
         (groups of .XXX thousands), immune to superscript-cent corruption.
      2. FALLBACK regex — loose capture for edge cases, with a
         suspicion warning if the amount looks inflated.

    Returns a result dict if successful, None if the text doesn't
    match receipt patterns.
    """
    # Detection: must start with "comprobante de pago" OR contain "ttoottaall"
    is_comprobante = cleaned.startswith("comprobante de pago")
    has_total_marker = "ttoottaall" in cleaned

    if not (is_comprobante or has_total_marker):
        return None

    logger.info("📄 [RECEIPT] Comprobante de Mercado Pago detectado")

    # ── Extract monto — strict regex first ───────────────────────
    monto: float | None = None

    strict_match = _RE_PDF_MONTO_STRICT.search(cleaned)
    if strict_match:
        try:
            monto = _parse_receipt_monto(strict_match)
            logger.info(
                "📄 [RECEIPT] Monto extraído (regex estricta): $%.2f",
                monto,
            )
        except (ValueError, IndexError) as exc:
            logger.warning(
                "📄 [RECEIPT] Error parseando monto estricto: %s", exc
            )

    # ── Fallback — loose regex if strict found nothing ───────────
    if monto is None or monto <= 0:
        fallback_match = _RE_PDF_MONTO_FALLBACK.search(cleaned)
        if not fallback_match:
            logger.warning(
                "📄 [RECEIPT] No se encontró monto en el comprobante"
            )
            return None

        try:
            monto = _parse_monto_ar(fallback_match.group(1))
            logger.warning(
                "📄 [RECEIPT] Monto extraído por FALLBACK (posible "
                "superíndice corrupto): $%.2f — revisar manualmente",
                monto,
            )
        except (ValueError, IndexError) as exc:
            logger.warning(
                "📄 [RECEIPT] Error parseando monto fallback: %s", exc
            )
            return None

    if monto is None or monto <= 0:
        logger.warning("📄 [RECEIPT] Monto inválido: %s", monto)
        return None

    # ── Suspicion alert for inflated amounts ─────────────────────
    if monto > 1_000_000:
        logger.warning(
            "⚠️ [RECEIPT] Monto sospechosamente alto: $%.2f — "
            "posible corrupción por superíndice de centavos",
            monto,
        )

    # ── Extract categoría from título ────────────────────────────
    titulo_match = _RE_PDF_TITULO.search(cleaned)
    if titulo_match:
        titulo_raw = titulo_match.group(1).strip()
        categoria = _normalizar_categoria(titulo_raw)
        logger.info(
            "📄 [RECEIPT] Título extraído: '%s' → categoría: '%s'",
            titulo_raw,
            categoria,
        )
    else:
        categoria = "Comprobante MP"
        logger.info("📄 [RECEIPT] Sin título, usando categoría default")

    logger.info(
        "📄 [RECEIPT] Costo $0 - Egreso detectado: monto=%.2f categoria='%s'",
        monto,
        categoria,
    )

    return _build_result(
        tipo="EGRESO",
        monto=monto,
        categoria=categoria,
        nota=f"Comprobante MP: ${monto:,.2f} en {categoria}",
        proveedor_usado="regex_pdf",
        confianza=0.9,
    )


async def analyze_hybrid_message(texto: str) -> dict:
    """
    Analyse an incoming message using deterministic regex rules.

    Parameters
    ----------
    texto : str
        Raw text message from the user.

    Returns
    -------
    dict
        A dict with keys: tipo, monto, categoria, nota, proveedor_usado, confianza.
    """
    cleaned = texto.strip().lower()
    logger.info("hybrid_nlp: cleaned input='%s'", cleaned)

    # ── Fast Path -1 — Cancel / Undo ─────────────────────────────
    if cleaned in _CANCEL_KEYWORDS or _RE_CANCEL_PHRASE.match(cleaned):
        logger.info(
            "↩️ [FAST PATH LOCAL] Intención de cancelación detectada: '%s'",
            cleaned,
        )
        return _build_result(
            tipo="CANCELAR",
            monto=0.0,
            categoria="Sistema",
            nota="cancelar_ultimo",
            proveedor_usado="regex_local",
            confianza=1.0,
        )

    # ── Fast Path 0 — Mercado Pago PDF receipt ──────────────────
    pdf_result = _try_parse_pdf_receipt(cleaned)
    if pdf_result is not None:
        return pdf_result

    # ── Fast Path 1 — Query keywords ────────────────────────────
    if cleaned in _QUERY_KEYWORDS:
        logger.info(
            "⚡ [FAST PATH LOCAL] Costo $0 - Consulta detectada por keyword: '%s'",
            cleaned,
        )
        return _build_result(
            tipo="CONSULTA",
            nota="consulta_saldo",
        )

    # ── Fast Path 2 — <monto> <categoría> ───────────────────────
    match = _RE_MONTO_CATEGORIA.match(cleaned)
    if match:
        monto = _parse_monto(match.group(1))
        categoria = _normalizar_categoria(match.group(2))
        logger.info(
            "⚡ [FAST PATH LOCAL] Costo $0 - Egreso detectado: monto=%.2f categoria='%s'",
            monto,
            categoria,
        )
        return _build_result(
            tipo="EGRESO",
            monto=monto,
            categoria=categoria,
            nota=f"{monto} {categoria}",
        )

    # ── Fast Path 3 — <verbo_gasto> <monto> [en|de] <categoría> ─
    match = _RE_VERBO_MONTO_CATEGORIA.match(cleaned)
    if match:
        monto = _parse_monto(match.group(1))
        categoria = _normalizar_categoria(match.group(2))
        logger.info(
            "⚡ [FAST PATH LOCAL] Costo $0 - Verbo+egreso detectado: monto=%.2f categoria='%s'",
            monto,
            categoria,
        )
        return _build_result(
            tipo="EGRESO",
            monto=monto,
            categoria=categoria,
            nota=f"Gasto {monto} en {categoria}",
        )

    # ── Fast Path 4 — <verbo_ingreso> <monto> [de|por] <concepto>
    match = _RE_INCOME.match(cleaned)
    if match:
        monto = _parse_monto(match.group(1))
        categoria = _normalizar_categoria_ingreso(match.group(2))
        logger.info(
            "💰 [FAST PATH LOCAL] Costo $0 - Ingreso detectado: monto=%.2f categoria='%s'",
            monto,
            categoria,
        )
        return _build_result(
            tipo="INGRESO",
            monto=monto,
            categoria=categoria,
            nota=f"Ingreso {monto} de {categoria}",
        )

    # ── No match — deterministic rejection ────────────────────────
    logger.warning(
        "❌ [LOCAL ENGINE] Ninguna regex hizo match. Mensaje rechazado: '%s'",
        cleaned[:80],
    )
    return _build_result(
        tipo="DESCONOCIDO",
        monto=0.0,
        categoria="Error",
        nota="No se pudo interpretar el mensaje.",
        proveedor_usado="regex_local",
        confianza=0.0,
    )
