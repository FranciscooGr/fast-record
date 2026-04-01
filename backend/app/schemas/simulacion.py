"""
Pydantic schemas for the message simulator.

- MensajeSimulado: request body (telefono + texto_mensaje)
- DatosFinancieros: structured output from the LLM
- SaldoActual: computed balance envelope
- SimulacionResponse: full response envelope
- SimulacionErrorResponse: error envelope when the LLM fails
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal


# ── Request ─────────────────────────────────────────────────────
class MensajeSimulado(BaseModel):
    """Payload sent by the developer to simulate a WhatsApp message."""

    telefono: str = Field(
        ...,
        min_length=8,
        max_length=20,
        examples=["+5491122334455"],
        description="Phone number of the simulated user.",
    )
    texto_mensaje: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=["Pagué 1500 de pizza con amigos"],
        description="Raw text message to be parsed by the LLM.",
    )

    @field_validator("texto_mensaje")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("texto_mensaje no puede estar vacío o ser solo espacios")
        return v.strip()


# ── LLM structured output ──────────────────────────────────────
class DatosFinancieros(BaseModel):
    """Validated financial data extracted by the LLM.
    Must contain exactly these four keys."""

    tipo: Literal["INGRESO", "EGRESO", "CONSULTA"] = Field(
        ...,
        description="Type of intention — INGRESO, EGRESO, or CONSULTA.",
    )
    monto: float = Field(
        ...,
        ge=0,
        description="Positive numeric amount. 0 for CONSULTA.",
    )
    categoria: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category (e.g. Comida, Sueldo, Fondo inicial, saldo).",
    )
    nota: str = Field(
        ...,
        max_length=500,
        description="Short descriptive note about the movement.",
    )


# ── Saldo calculado ────────────────────────────────────────────
class SaldoActual(BaseModel):
    """Dynamically computed balance — NEVER stored in the DB."""

    ingresos_total: float = Field(
        ..., description="Sum of all INGRESO movements."
    )
    egresos_total: float = Field(
        ..., description="Sum of all EGRESO movements."
    )
    saldo: float = Field(
        ..., description="ingresos_total - egresos_total"
    )


# ── Response (success) ─────────────────────────────────────────
class SimulacionResponse(BaseModel):
    """Successful simulation response."""

    ok: bool = True
    datos_parseados: DatosFinancieros
    mensaje_usuario: str = Field(
        ...,
        description="Confirmation message that would be sent back to the WhatsApp user.",
    )
    saldo_actual: SaldoActual = Field(
        ...,
        description="Current computed balance after processing the message.",
    )


# ── Response (error) ───────────────────────────────────────────
class SimulacionErrorResponse(BaseModel):
    """Error response when the LLM fails."""

    ok: bool = False
    error: str
