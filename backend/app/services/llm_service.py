"""
LLM Service — Groq financial data extraction (async).

Sends the user's text message along with a strict system prompt to
Groq (via AsyncGroq) and returns a validated JSON with:
  { tipo, monto, categoria, nota }

Fallback: if the LLM fails or returns unparseable data, the function
returns a safe default with categoria="Otros".

SDK required:  groq
Install with:  pip install groq
"""

import json
import logging

from groq import AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── System prompt — strict JSON-only output ─────────────────────
SYSTEM_PROMPT = """\
Eres un asistente financiero que clasifica mensajes de texto de usuarios.

Tu ÚNICA tarea es analizar el mensaje del usuario y devolver EXCLUSIVAMENTE
un objeto JSON válido con estas 4 claves (sin texto adicional, sin markdown,
sin backticks, sin explicaciones):

{
  "tipo": "INGRESO" | "EGRESO" | "CONSULTA",
  "monto": <número positivo o 0>,
  "categoria": "<categoría>",
  "nota": "<breve descripción>"
}

INTENCIONES QUE DEBÉS DETECTAR:

1. EGRESO (gasto): "pagué X", "gasté X", "compré X por Y".
   → tipo="EGRESO", monto=X, categoria=<categoría del gasto>, nota=<descripción>

2. INGRESO (ingreso genérico): "me pagaron X", "cobré X".
   → tipo="INGRESO", monto=X, categoria=<categoría del ingreso>, nota=<descripción>

3. ESTABLECER_FONDO: "mi fondo es X", "tengo X de presupuesto", "mi saldo inicial es X".
   → tipo="INGRESO", monto=X, categoria="Fondo inicial", nota=<descripción>

4. SUMAR_FONDO: "sumame X", "agregame X", "deposité X", "cobré X", "me transfirieron X".
   → tipo="INGRESO", monto=X, categoria="Depósito", nota=<descripción>

5. CONSULTAR_SALDO: "cuánto tengo", "mi saldo", "cuánto me queda", "cómo voy".
   → tipo="CONSULTA", monto=0, categoria="saldo", nota="consulta_saldo"

REGLAS ESTRICTAS:
1. "tipo" SOLO puede ser "INGRESO", "EGRESO" o "CONSULTA". Nada más.
2. "monto" debe ser un número positivo. Para CONSULTA el monto es 0.
3. "categoria" debe ser una palabra o frase corta que clasifique el
   movimiento (ej: Comida, Transporte, Sueldo, Alquiler, Servicios,
   Entretenimiento, Salud, Educación, Fondo inicial, Depósito, saldo, Otros).
4. "nota" es una descripción brevísima basada en lo que dijo el usuario.
5. NUNCA respondas con texto fuera del JSON.
6. NUNCA uses markdown, backticks, ni ```json```.
7. Si no podés clasificar el mensaje, usá tipo="EGRESO", categoria="Otros".

Respondé SOLO el JSON. Nada más.
"""

# ── Groq model — ultra-fast, free tier ──────────────────────────
_MODEL_NAME = "llama-3.3-70b-versatile"

# ── Fallback default when LLM completely fails ─────────────────
_FALLBACK_DEFAULT = {
    "tipo": "EGRESO",
    "monto": 0,
    "categoria": "Otros",
    "nota": "No se pudo procesar el mensaje",
    "proveedor_usado": "fallback_otros",
    "confianza": 0.0,
}


def _get_client() -> AsyncGroq:
    """Create an async Groq client configured with the API key from settings."""
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


async def extract_financial_data(text: str) -> dict:
    """
    Send the user's message to Groq and return parsed financial data.

    Parameters
    ----------
    text : str
        The raw text message from the user.

    Returns
    -------
    dict
        A dict with keys: tipo, monto, categoria, nota, proveedor_usado, confianza.
        On complete failure, returns a safe fallback with categoria="Otros".
    """
    client = _get_client()

    logger.info("Sending message to Groq (%s): %s", _MODEL_NAME, text[:80])

    try:
        response = await client.chat.completions.create(
            model=_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info("Groq raw response: %s", raw_text[:200])

        parsed = json.loads(raw_text)

    except json.JSONDecodeError as exc:
        logger.error("Groq returned invalid JSON: %s", str(exc))
        return {**_FALLBACK_DEFAULT, "raw_response": str(exc)}

    except Exception as exc:
        logger.error("Groq API call failed: %s", str(exc))
        return {**_FALLBACK_DEFAULT, "raw_response": str(exc)}

    # Validate required keys
    required_keys = {"tipo", "monto", "categoria", "nota"}
    missing = required_keys - set(parsed.keys())
    if missing:
        logger.error("Groq JSON missing keys: %s", missing)
        return {**_FALLBACK_DEFAULT, "raw_response": raw_text}

    # Enrich with orchestration metadata
    parsed["proveedor_usado"] = "groq"
    parsed["confianza"] = 1.0
    parsed.setdefault("raw_response", raw_text)

    return parsed
