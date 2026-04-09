"""
Hybrid NLP Service — Fast Path (Regex) + Slow Path (LLM).

Implements the "Fast Path / Slow Path" architectural pattern to reduce
LLM API costs.  Simple, deterministic messages are resolved locally
with Python regex; only ambiguous messages fall through to Groq.

Processing order:
  1. Fast Path 1 — Balance / query keywords   → CONSULTA
  2. Fast Path 2 — <monto> <categoría>        → EGRESO
  3. Fast Path 3 — <verbo> <monto> <categoría> → EGRESO
  4. Slow Path   — LLM via extract_financial_data
"""

import logging
import re

from app.services.llm_service import extract_financial_data

logger = logging.getLogger(__name__)

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
    rf"^{_SPENDING_VERBS}\s+(\d+(?:[.,]\d{1,2})?)\s*(?:(?:en|de)\s+)?(.*)$",
)


def _parse_monto(raw: str) -> float:
    """Normalize comma-decimal to dot-decimal and parse to float."""
    return float(raw.replace(",", "."))


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


async def analyze_hybrid_message(texto: str) -> dict:
    """
    Analyse an incoming message with regex first; fall back to LLM.

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

    # ── Fast Path 3 — <verbo> <monto> [en|de] <categoría> ──────
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

    # ── Slow Path — delegate to LLM ──────────────────────────────
    logger.info(
        "🤖 [SLOW PATH LLM] Regex falló. Delegando a IA externa para: '%s'",
        cleaned[:80],
    )
    return await extract_financial_data(texto)
