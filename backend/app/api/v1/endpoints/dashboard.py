"""
Dashboard endpoint — returns summary data filtered by date range.

Access is keyed by ``public_id`` (8-char UUID slug) — no JWT required.

Query parameters:
  - public_id  (required): The user's public identifier.
  - start_date (optional): ISO date string (YYYY-MM-DD). Defaults to 1st of current month.
  - end_date   (optional): ISO date string (YYYY-MM-DD). Defaults to today.

All queries (balance, income, expenses, recent activity, category breakdown)
are scoped to the provided date window.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.api.v1.websockets import manager
from app.core.limiter import limiter
from app.db.session import AsyncSessionLocal
from app.models.movement import Movement, TipoMovimiento
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _default_date_range() -> tuple[date, date]:
    """Return (first day of current month, today) as the default range."""
    today = date.today()
    return today.replace(day=1), today


async def _resolve_user_by_public_id(public_id: str, db: AsyncSession) -> User:
    """Look up a user by public_id or raise 404."""
    stmt = select(User).where(User.public_id == public_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/summary")
@limiter.limit("15/minute")
async def get_dashboard_summary(
    request: Request,
    public_id: str = Query(..., description="Public ID of the user"),
    start_date: date | None = Query(None, description="Start of period (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End of period (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    user = await _resolve_user_by_public_id(public_id, db)
    user_id = user.id

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


@router.websocket("/ws/{public_id}")
async def ws_dashboard(websocket: WebSocket, public_id: str):
    """Keep a WebSocket open so the frontend receives live update signals."""
    # Resolve internal user_id from public_id
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.public_id == public_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

    if user is None:
        await websocket.close(code=4004)
        return

    usuario_id = user.id
    await manager.connect(usuario_id, websocket)
    try:
        while True:
            # Keep the connection alive; ignore any client-sent frames
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(usuario_id, websocket)
