"""
Movement service — create movements and calculate balance.

The balance (saldo) is NEVER stored — it is ALWAYS computed dynamically
by aggregating movements via SUM.  This is an inviolable business rule.
"""

import logging
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement import Movement, TipoMovimiento
from app.api.v1.websockets import manager

logger = logging.getLogger(__name__)


async def crear_movimiento(
    usuario_id: int,
    tipo: str,
    monto: float,
    categoria: str,
    nota: str,
    db: AsyncSession,
) -> Movement:
    """
    Insert a new movement record and return the created ORM instance.

    Parameters
    ----------
    usuario_id : int
        FK to the users table.
    tipo : str
        "INGRESO" or "EGRESO".
    monto : float
        Positive amount.
    categoria : str
        Category label.
    nota : str
        Short descriptive note.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    Movement
        The persisted Movement instance with its generated id.
    """
    movement = Movement(
        usuario_id=usuario_id,
        tipo=TipoMovimiento(tipo),
        monto=Decimal(str(monto)),
        categoria=categoria,
        nota=nota,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    logger.info(
        "Movement created: id=%d user=%d tipo=%s monto=%s cat=%s",
        movement.id,
        usuario_id,
        tipo,
        monto,
        categoria,
    )

    # ── Notify connected dashboard clients in real time ─────────
    await manager.broadcast(usuario_id, "update_dashboard")

    return movement


async def calcular_saldo(usuario_id: int, db: AsyncSession) -> dict:
    """
    Compute the running balance from the movements table.

    The balance is NEVER read from a column — it is calculated:
        saldo = SUM(INGRESO) - SUM(EGRESO)

    Parameters
    ----------
    usuario_id : int
        The user whose balance to compute.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    dict
        {
            "ingresos_total": float,
            "egresos_total": float,
            "saldo": float  # ingresos - egresos
        }
    """
    # SUM of INGRESO
    stmt_ingresos = select(
        func.coalesce(func.sum(Movement.monto), 0)
    ).where(
        Movement.usuario_id == usuario_id,
        Movement.tipo == TipoMovimiento.INGRESO,
    )
    result_ing = await db.execute(stmt_ingresos)
    ingresos_total = float(result_ing.scalar_one())

    # SUM of EGRESO
    stmt_egresos = select(
        func.coalesce(func.sum(Movement.monto), 0)
    ).where(
        Movement.usuario_id == usuario_id,
        Movement.tipo == TipoMovimiento.EGRESO,
    )
    result_egr = await db.execute(stmt_egresos)
    egresos_total = float(result_egr.scalar_one())

    saldo = ingresos_total - egresos_total

    logger.info(
        "Balance for user=%d: ingresos=%.2f egresos=%.2f saldo=%.2f",
        usuario_id,
        ingresos_total,
        egresos_total,
        saldo,
    )

    return {
        "ingresos_total": ingresos_total,
        "egresos_total": egresos_total,
        "saldo": saldo,
    }


async def resetear_movimientos(usuario_id: int, db: AsyncSession) -> int:
    """
    Delete ALL movements for a given user.

    The balance becomes 0 automatically because it is always computed
    dynamically — no static column to update.

    Parameters
    ----------
    usuario_id : int
        The user whose movements to wipe.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    int
        Number of rows deleted.
    """
    stmt = delete(Movement).where(Movement.usuario_id == usuario_id)
    result = await db.execute(stmt)
    await db.commit()

    deleted = result.rowcount
    logger.info("Reset: deleted %d movements for user=%d", deleted, usuario_id)

    # ── Notify connected dashboard clients ──────────────────────
    await manager.broadcast(usuario_id, "update_dashboard")

    return deleted
