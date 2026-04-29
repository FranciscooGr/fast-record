"""
Pydantic schemas for the Financial Reports endpoint.

All monetary values are computed dynamically — never from stored columns.
The "saldo" is ALWAYS an aggregate of movements, honouring the inviolable
business rule.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Individual metric models ───────────────────────────────────

class BalanceNeto(BaseModel):
    """Dynamic balance: ingresos - egresos within the requested period."""

    ingresos_total: float = Field(
        ..., description="Sum of all INGRESO movements in the period."
    )
    egresos_total: float = Field(
        ..., description="Sum of all EGRESO movements in the period."
    )
    balance: float = Field(
        ..., description="ingresos_total - egresos_total (computed, never stored)."
    )


class TasaAhorro(BaseModel):
    """Savings rate = (ingresos - egresos) / ingresos × 100."""

    tasa_porcentaje: float = Field(
        ..., description="Savings rate as a percentage (0–100). 0 if no income."
    )


class GastoPromedioDiario(BaseModel):
    """Average daily expense within the period."""

    promedio: float = Field(
        ..., description="Total EGRESO ÷ number of days in the period."
    )
    dias_periodo: int = Field(
        ..., description="Number of calendar days used as the denominator."
    )


class CategoriaGasto(BaseModel):
    """A single category, its total expense, and real percentage."""

    categoria: str
    total: float
    porcentaje: float = Field(
        ...,
        description="Percentage of this category vs total general expenses in the period.",
    )


class TopCategorias(BaseModel):
    """Top 3 expense categories ordered by total descending."""

    total_general: float = Field(
        ...,
        description="Sum of ALL egresos in the period (not just the top N).",
    )
    categorias: list[CategoriaGasto] = Field(
        ..., description="Up to 3 categories with the highest expense."
    )


class GastosHormiga(BaseModel):
    """Ant expenses: individual EGRESO movements with monto < 5 000."""

    total: float = Field(
        ..., description="Sum of all EGRESO with monto < 5000."
    )
    cantidad: int = Field(
        ..., description="Number of ant-expense movements."
    )
    porcentaje_impacto: float = Field(
        ...,
        description=(
            "Impact as percentage of total income: "
            "(gastos_hormiga_total / ingresos_total) × 100."
        ),
    )


# ── Mayor Crecimiento ─────────────────────────────────────────

class MayorCrecimiento(BaseModel):
    """Category with the highest period-over-period growth."""

    categoria: str = Field(
        ..., description="Name of the category that grew the most."
    )
    porcentaje: float = Field(
        ..., description="Percentage variation: ((A-B)/B)×100."
    )
    tendencia: str = Field(
        ..., description="Human-readable trend description."
    )


# ── Periodo ────────────────────────────────────────────────────

class PeriodoInfo(BaseModel):
    """Date window applied to the report."""

    start_date: str = Field(..., description="ISO start date (YYYY-MM-DD).")
    end_date: str = Field(..., description="ISO end date (YYYY-MM-DD).")


# ── Aggregated response ───────────────────────────────────────

class InformesResponse(BaseModel):
    """Full financial report response."""

    ok: bool = True
    balance_neto: BalanceNeto
    tasa_ahorro: TasaAhorro
    gasto_promedio_diario: GastoPromedioDiario
    top_categorias: TopCategorias
    gastos_hormiga: GastosHormiga
    mayor_crecimiento: Optional[MayorCrecimiento] = Field(
        None,
        description="Category with greatest growth vs previous period. Null if insufficient data.",
    )
    periodo: PeriodoInfo
