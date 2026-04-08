from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from app.api.v1.deps import get_db, get_current_user
from app.models.movement import Movement, TipoMovimiento

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = int(current_user["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    # 1. Obtenemos ingresos totales y egresos totales
    stmt_totals = select(
        func.coalesce(func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.INGRESO), 0).label("ingresos"),
        func.coalesce(func.sum(Movement.monto).filter(Movement.tipo == TipoMovimiento.EGRESO), 0).label("egresos")
    ).where(Movement.usuario_id == user_id)
    
    result_totals = await db.execute(stmt_totals)
    row = result_totals.one()
    ingresos = float(row.ingresos)
    egresos = float(row.egresos)
    saldo_actual = ingresos - egresos
    
    # 2. Movimientos recientes (últimos 5)
    stmt_recent = select(Movement).where(Movement.usuario_id == user_id).order_by(Movement.fecha.desc()).limit(5)
    result_recent = await db.execute(stmt_recent)
    recent = result_recent.scalars().all()
    
    movimientos_recientes = [
        {
            "id": mov.id,
            "name": mov.nota or ("Ingreso" if mov.tipo == TipoMovimiento.INGRESO else "Gasto general"),
            "category": mov.categoria,
            "fecha": mov.fecha.isoformat(),
            "amount": float(mov.monto) if mov.tipo == TipoMovimiento.INGRESO else -float(mov.monto),
            "tipo": mov.tipo.value
        }
        for mov in recent
    ]
    
    # 3. Gastos por categoría para el gráfico de torta
    stmt_cat = select(
        Movement.categoria,
        func.sum(Movement.monto).label("total")
    ).where(Movement.usuario_id == user_id, Movement.tipo == TipoMovimiento.EGRESO).group_by(Movement.categoria)
    
    result_cat = await db.execute(stmt_cat)
    gastos_por_categoria = []
    
    # Paleta de colores acorde al diseño frontend (brand y surfaces)
    colors = ['#2d8a2d', '#0f3c0f', '#aadcaa', '#e8f0e8', '#5a6e5a', '#9aaa9a']
    for idx, r in enumerate(result_cat.all()):
        gastos_por_categoria.append({
            "name": r.categoria,
            "value": float(r.total),
            "color": colors[idx % len(colors)]
        })
        
    return {
        "saldo_actual": saldo_actual,
        "ingresos_totales": ingresos,
        "egresos_totales": egresos,
        "movimientos_recientes": movimientos_recientes,
        "gastos_por_categoria": gastos_por_categoria
    }
