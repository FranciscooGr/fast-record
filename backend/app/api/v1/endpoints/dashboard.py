"""
Dashboard endpoint — returns summary data filtered by date range.

Query parameters:
  - start_date (optional): ISO date string (YYYY-MM-DD). Defaults to 1st of current month.
  - end_date   (optional): ISO date string (YYYY-MM-DD). Defaults to today.

All queries (balance, income, expenses, recent activity, category breakdown)
are scoped to the provided date window.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_current_user
from app.models.movement import Movement, TipoMovimiento

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _default_date_range() -> tuple[date, date]:
    """Return (first day of current month, today) as the default range."""
    today = date.today()
    return today.replace(day=1), today


@router.get("/summary")
async def get_dashboard_summary(
    start_date: date | None = Query(None, description="Start of period (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End of period (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = int(current_user["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    # ── Resolve date range (defaults to current month) ──────────
    if start_date is None or end_date is None:
        default_start, default_end = _default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end

    # Convert dates to timezone-aware datetimes for the WHERE clause
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # ── Base filter: user + date range ──────────────────────────
    base_filter = [
        Movement.usuario_id == user_id,
        Movement.fecha >= start_dt,
        Movement.fecha <= end_dt,
    ]

    # ── Totals (global historical) ──────────────────────────────
    stmt_historico = select(
        func.coalesce(
            func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.INGRESO), 0
        ).label("ingresos"),
        func.coalesce(
            func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.EGRESO), 0
        ).label("egresos"),
    ).where(Movement.usuario_id == user_id)

    result_historico = await db.execute(stmt_historico)
    row_hist = result_historico.one()
    saldo_historico_global = float(row_hist.ingresos) - float(row_hist.egresos)

    # 1. Totals (income / expenses within period)
    stmt_totals = select(
        func.coalesce(
            func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.INGRESO), 0
        ).label("ingresos"),
        func.coalesce(
            func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.EGRESO), 0
        ).label("egresos"),
    ).where(*base_filter)

    result_totals = await db.execute(stmt_totals)
    row = result_totals.one()
    ingresos = float(row.ingresos)
    egresos = float(row.egresos)
    saldo_periodo = ingresos - egresos

    # 2. Recent movements within period (last 10)
    stmt_recent = (
        select(Movement)
        .where(*base_filter)
        .order_by(Movement.fecha.desc())
        .limit(10)
    )
    result_recent = await db.execute(stmt_recent)
    recent = result_recent.scalars().all()

    movimientos_recientes = [
        {
            "id": mov.id,
            "name": mov.nota or ("Ingreso" if mov.tipo == TipoMovimiento.INGRESO else "Gasto general"),
            "category": mov.categoria,
            "fecha": mov.fecha.isoformat(),
            "amount": float(mov.monto) if mov.tipo == TipoMovimiento.INGRESO else -float(mov.monto),
            "tipo": mov.tipo.value,
        }
        for mov in recent
    ]

    # 3. Expense breakdown by category within period
    stmt_cat = (
        select(Movement.categoria, func.sum(Movement.monto).label("total"))
        .where(*base_filter, Movement.tipo == TipoMovimiento.EGRESO)
        .group_by(Movement.categoria)
    )
    result_cat = await db.execute(stmt_cat)

    colors = [
        "#2d8a2d", "#0f3c0f", "#aadcaa", "#e8f0e8",
        "#5a6e5a", "#9aaa9a", "#3ca03c", "#174017",
    ]
    gastos_por_categoria = [
        {
            "name": r.categoria,
            "value": float(r.total),
            "color": colors[idx % len(colors)],
        }
        for idx, r in enumerate(result_cat.all())
    ]

    return {
        "saldo_historico_global": saldo_historico_global,
        "saldo_periodo": saldo_periodo,
        "ingresos_totales": ingresos,
        "egresos_totales": egresos,
        "movimientos_recientes": movimientos_recientes,
        "gastos_por_categoria": gastos_por_categoria,
        "periodo": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    }
