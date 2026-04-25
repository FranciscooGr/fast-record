"""
Informes service — financial report calculations.

Every metric is computed via SQL aggregation over the
``movements`` table.  The balance is NEVER read from a stored column;
it is ALWAYS calculated dynamically (inviolable business rule).

All functions are async and receive an ``AsyncSession`` — business
logic lives here, not in the endpoint layer.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement import Movement, TipoMovimiento

logger = logging.getLogger(__name__)

# ── Threshold for "gastos hormiga" ─────────────────────────────
GASTO_HORMIGA_LIMITE = 5_000


def _build_period_filter(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> list:
    """Return a reusable list of WHERE clauses scoped to user + period."""
    return [
        Movement.usuario_id == user_id,
        Movement.fecha >= start_dt,
        Movement.fecha <= end_dt,
    ]


async def calcular_balance_neto(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
) -> dict:
    """
    Compute total income, total expenses, and net balance.

    The balance is:  SUM(INGRESO) - SUM(EGRESO)
    — computed dynamically, never read from a column.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)

    stmt = select(
        func.coalesce(
            func.sum(Movement.monto).filter(
                Movement.tipo == TipoMovimiento.INGRESO
            ),
            0,
        ).label("ingresos"),
        func.coalesce(
            func.sum(Movement.monto).filter(
                Movement.tipo == TipoMovimiento.EGRESO
            ),
            0,
        ).label("egresos"),
    ).where(*base)

    result = await db.execute(stmt)
    row = result.one()

    ingresos = float(row.ingresos)
    egresos = float(row.egresos)
    balance = ingresos - egresos

    logger.info(
        "balance_neto user=%d: ingresos=%.2f egresos=%.2f balance=%.2f",
        user_id, ingresos, egresos, balance,
    )

    return {
        "ingresos_total": ingresos,
        "egresos_total": egresos,
        "balance": balance,
    }


async def calcular_tasa_ahorro(
    ingresos_total: float,
    egresos_total: float,
) -> dict:
    """
    Savings rate = (ingresos - egresos) / ingresos × 100.

    Returns 0 % when there is no income (avoids division by zero).
    """
    if ingresos_total == 0:
        return {"tasa_porcentaje": 0.0}

    tasa = ((ingresos_total - egresos_total) / ingresos_total) * 100
    # Clamp to reasonable range: could be negative if expenses > income
    return {"tasa_porcentaje": round(tasa, 2)}


async def calcular_gasto_promedio_diario(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
) -> dict:
    """
    Average daily expense = total EGRESO ÷ number of calendar days.

    If the period spans 0 days (same-day query), we use 1 day.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)

    stmt = select(
        func.coalesce(
            func.sum(Movement.monto).filter(
                Movement.tipo == TipoMovimiento.EGRESO
            ),
            0,
        ).label("total_egresos"),
    ).where(*base)

    result = await db.execute(stmt)
    total_egresos = float(result.scalar_one())

    dias = max((end_dt.date() - start_dt.date()).days, 1)

    return {
        "promedio": round(total_egresos / dias, 2),
        "dias_periodo": dias,
    }


async def calcular_top_categorias(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
    *,
    top_n: int = 3,
) -> dict:
    """
    Top N expense categories by total amount (descending).

    Uses GROUP BY + ORDER BY + LIMIT.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)

    stmt = (
        select(
            Movement.categoria,
            func.sum(Movement.monto).label("total"),
        )
        .where(*base, Movement.tipo == TipoMovimiento.EGRESO)
        .group_by(Movement.categoria)
        .order_by(func.sum(Movement.monto).desc())
        .limit(top_n)
    )

    result = await db.execute(stmt)
    categorias = [
        {"categoria": row.categoria, "total": float(row.total)}
        for row in result.all()
    ]

    return {"categorias": categorias}


async def calcular_gastos_hormiga(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
) -> dict:
    """
    Ant expenses: EGRESO movements with monto < GASTO_HORMIGA_LIMITE.

    Returns the aggregate sum AND count of those micro-expenses.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)

    stmt = select(
        func.coalesce(func.sum(Movement.monto), 0).label("total"),
        func.count(Movement.id).label("cantidad"),
    ).where(
        *base,
        Movement.tipo == TipoMovimiento.EGRESO,
        Movement.monto < GASTO_HORMIGA_LIMITE,
    )

    result = await db.execute(stmt)
    row = result.one()

    return {
        "total": float(row.total),
        "cantidad": int(row.cantidad),
    }


# ── Orchestrator ───────────────────────────────────────────────

async def generar_informe_financiero(
    user_id: int,
    start_date: date | None,
    end_date: date | None,
    db: AsyncSession,
) -> dict:
    """
    Orchestrate all metric calculations and return the complete report.

    Defaults to the last 30 days if no dates are provided.

    Parameters
    ----------
    user_id : int
        FK to the users table.
    start_date, end_date : date | None
        Optional date window.  Defaults: last 30 days.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    dict
        Ready-to-serialise payload matching ``InformesResponse``.
    """
    # ── Resolve defaults ────────────────────────────────────────
    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today - timedelta(days=30)

    # Convert to tz-aware datetimes for the WHERE clause
    start_dt = datetime(
        start_date.year, start_date.month, start_date.day,
        tzinfo=timezone.utc,
    )
    end_dt = datetime(
        end_date.year, end_date.month, end_date.day,
        23, 59, 59, tzinfo=timezone.utc,
    )

    # ── Run calculations ────────────────────────────────────────
    balance = await calcular_balance_neto(user_id, start_dt, end_dt, db)

    tasa = await calcular_tasa_ahorro(
        balance["ingresos_total"], balance["egresos_total"],
    )

    gasto_diario = await calcular_gasto_promedio_diario(
        user_id, start_dt, end_dt, db,
    )

    top_cats = await calcular_top_categorias(
        user_id, start_dt, end_dt, db,
    )

    hormiga = await calcular_gastos_hormiga(
        user_id, start_dt, end_dt, db,
    )

    logger.info(
        "Financial report generated for user=%d period=%s→%s",
        user_id, start_date.isoformat(), end_date.isoformat(),
    )

    return {
        "ok": True,
        "balance_neto": balance,
        "tasa_ahorro": tasa,
        "gasto_promedio_diario": gasto_diario,
        "top_categorias": top_cats,
        "gastos_hormiga": hormiga,
        "periodo": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    }
