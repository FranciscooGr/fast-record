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

    1. Queries the **total general** of ALL egresos in the period.
    2. Queries the top N categories by amount.
    3. Computes each category's ``porcentaje`` against the total general
       (not against the top-N subtotal).

    Returns ``total_general`` alongside the list so the frontend can
    display accurate percentages.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)
    egreso_filter = [*base, Movement.tipo == TipoMovimiento.EGRESO]

    # ── 1. Total general de TODOS los egresos ───────────────────
    total_stmt = select(
        func.coalesce(func.sum(Movement.monto), 0).label("total_general"),
    ).where(*egreso_filter)

    total_general = float((await db.execute(total_stmt)).scalar_one())

    # ── 2. Top N categorías ─────────────────────────────────────
    top_stmt = (
        select(
            Movement.categoria,
            func.sum(Movement.monto).label("total"),
        )
        .where(*egreso_filter)
        .group_by(Movement.categoria)
        .order_by(func.sum(Movement.monto).desc())
        .limit(top_n)
    )

    result = await db.execute(top_stmt)

    # ── 3. Porcentaje real contra el total general ──────────────
    categorias = [
        {
            "categoria": row.categoria,
            "total": float(row.total),
            "porcentaje": round(
                (float(row.total) / total_general) * 100, 2
            ) if total_general > 0 else 0.0,
        }
        for row in result.all()
    ]

    return {"total_general": total_general, "categorias": categorias}


async def calcular_gastos_hormiga(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
    *,
    ingresos_total: float = 0.0,
) -> dict:
    """
    Ant expenses: EGRESO movements with monto < GASTO_HORMIGA_LIMITE.

    Returns the aggregate sum, count, and the percentage impact relative
    to the user's total income (``ingresos_total``).

    ``porcentaje_impacto`` = (gastos_hormiga_total / ingresos_total) × 100.
    When ``ingresos_total`` is 0 the percentage is 0 (avoids ZeroDivisionError).
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

    total = float(row.total)
    porcentaje = round((total / ingresos_total) * 100, 2) if ingresos_total > 0 else 0.0

    return {
        "total": total,
        "cantidad": int(row.cantidad),
        "porcentaje_impacto": porcentaje,
    }


async def _category_totals(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
) -> dict[str, float]:
    """
    Return ``{category_name: total_amount}`` for ALL movement types
    within the given period (both INGRESO and EGRESO combined).

    Used internally to compare two periods and find the category
    with the greatest positive growth.
    """
    base = _build_period_filter(user_id, start_dt, end_dt)

    stmt = (
        select(
            Movement.categoria,
            func.sum(Movement.monto).label("total"),
        )
        .where(*base)
        .group_by(Movement.categoria)
    )

    result = await db.execute(stmt)
    return {row.categoria: float(row.total) for row in result.all()}


async def calcular_mayor_crecimiento(
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
    db: AsyncSession,
) -> dict | None:
    """
    Period-vs-period growth analysis.

    Compares the current period (A) against an equivalent-length
    previous period (B) and returns the category with the highest
    positive percentage variation::

        variation = ((monto_A - monto_B) / monto_B) × 100

    Edge cases
    ----------
    * ``monto_B == 0`` (new category): treated as +100 % growth.
    * No positive growth in any category: returns ``None``.
    * No data at all in either period: returns ``None``.
    """
    # ── Compute the equivalent previous period ──────────────────
    period_days = max((end_dt.date() - start_dt.date()).days, 1)
    prev_end_dt = start_dt - timedelta(seconds=1)
    prev_start_dt = datetime(
        (start_dt.date() - timedelta(days=period_days)).year,
        (start_dt.date() - timedelta(days=period_days)).month,
        (start_dt.date() - timedelta(days=period_days)).day,
        tzinfo=timezone.utc,
    )

    # ── Fetch category totals for both periods ──────────────────
    totals_a = await _category_totals(user_id, start_dt, end_dt, db)
    totals_b = await _category_totals(user_id, prev_start_dt, prev_end_dt, db)

    if not totals_a:
        return None

    # ── Calculate variation per category ────────────────────────
    best: dict | None = None

    for cat, monto_a in totals_a.items():
        monto_b = totals_b.get(cat, 0.0)

        if monto_b > 0:
            variacion = ((monto_a - monto_b) / monto_b) * 100
        elif monto_a > 0:
            # New category with no previous data → 100 % growth
            variacion = 100.0
        else:
            continue

        if variacion <= 0:
            continue

        if best is None or variacion > best["porcentaje"]:
            best = {
                "categoria": cat,
                "porcentaje": round(variacion, 1),
                "tendencia": "Tendencia al alza este período",
            }

    if best is not None:
        logger.info(
            "mayor_crecimiento user=%d: %s +%.1f%%",
            user_id, best["categoria"], best["porcentaje"],
        )

    return best


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
        ingresos_total=balance["ingresos_total"],
    )

    crecimiento = await calcular_mayor_crecimiento(
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
        "mayor_crecimiento": crecimiento,
        "periodo": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    }
