"""
Movement service — create movements and calculate balance.

The balance (saldo) is NEVER stored — it is ALWAYS computed dynamically
by aggregating movements via SUM.  This is an inviolable business rule.
"""

import logging
from decimal import Decimal

from sqlalchemy import delete, func, select, update
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

    saldo = max(0.0, ingresos_total - egresos_total)

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


async def undo_last_movement(
    usuario_id: int,
    db: AsyncSession,
) -> dict:
    """
    Delete the most recent movement for a user and return undo details.

    The balance is recalculated dynamically after deletion — no stored
    column is ever modified.

    Parameters
    ----------
    usuario_id : int
        The user whose last movement to undo.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    dict
        On success:
            {"status": "success", "tipo": str, "monto": float,
             "categoria": str, "nuevo_saldo": float}
        On failure (no movements):
            {"status": "error", "message": str}
    """
    # ── Find the latest movement ────────────────────────────────
    stmt = (
        select(Movement)
        .where(Movement.usuario_id == usuario_id)
        .order_by(Movement.fecha.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_movement = result.scalar_one_or_none()

    if last_movement is None:
        logger.info(
            "Undo requested but user=%d has no movements", usuario_id
        )
        return {
            "status": "error",
            "message": "No tenés movimientos para cancelar.",
        }

    # ── Capture info before deletion ────────────────────────────
    tipo = last_movement.tipo.value          # "INGRESO" or "EGRESO"
    monto = float(last_movement.monto)
    categoria = last_movement.categoria
    movement_id = last_movement.id

    # ── Delete the movement ─────────────────────────────────────
    await db.delete(last_movement)
    await db.commit()

    logger.info(
        "Undo: deleted movement id=%d user=%d tipo=%s monto=%.2f cat=%s",
        movement_id,
        usuario_id,
        tipo,
        monto,
        categoria,
    )

    # ── Recalculate balance dynamically ─────────────────────────
    saldo_data = await calcular_saldo(usuario_id, db)

    # ── Notify connected dashboard clients ──────────────────────
    await manager.broadcast(usuario_id, "update_dashboard")

    return {
        "status": "success",
        "tipo": tipo,
        "monto": monto,
        "categoria": categoria,
        "nuevo_saldo": saldo_data["saldo"],
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


async def eliminar_movimiento(
    movement_id: int,
    usuario_id: int,
    db: AsyncSession,
) -> bool:
    """
    Delete a SINGLE movement — only if it belongs to the given user.

    IDOR protection: the WHERE clause filters by BOTH movement.id
    AND movement.usuario_id.  If the movement doesn't exist OR
    belongs to a different user, the result is the same: False.
    We intentionally don't distinguish the two cases to avoid
    leaking information about existing IDs.

    Parameters
    ----------
    movement_id : int
        Primary key of the movement to delete.
    usuario_id : int
        The authenticated user's ID.
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    bool
        True if a row was actually deleted, False otherwise.
    """
    stmt = delete(Movement).where(
        Movement.id == movement_id,
        Movement.usuario_id == usuario_id,
    )
    result = await db.execute(stmt)
    await db.commit()

    deleted = result.rowcount > 0

    if deleted:
        logger.info(
            "Movement deleted: id=%d by user=%d", movement_id, usuario_id
        )
        await manager.broadcast(usuario_id, "update_dashboard")
    else:
        logger.warning(
            "IDOR or 404: user=%d tried to delete movement_id=%d (no match)",
            usuario_id,
            movement_id,
        )

    return deleted


async def actualizar_movimiento(
    movement_id: int,
    usuario_id: int,
    db: AsyncSession,
    *,
    tipo: str | None = None,
    monto: float | None = None,
    categoria: str | None = None,
    nota: str | None = None,
) -> Movement | None:
    """
    Update a movement — only if it belongs to the given user.

    IDOR protection: same compound WHERE as eliminar_movimiento.

    Only provided (non-None) fields are updated; the rest stay
    unchanged.

    Parameters
    ----------
    movement_id : int
        Primary key of the movement to update.
    usuario_id : int
        The authenticated user's ID.
    db : AsyncSession
        The async SQLAlchemy session.
    tipo, monto, categoria, nota
        Optional fields to update.

    Returns
    -------
    Movement | None
        The updated Movement instance, or None if not found / IDOR.
    """
    # Build update dict from non-None values
    values: dict = {}
    if tipo is not None:
        values["tipo"] = TipoMovimiento(tipo)
    if monto is not None:
        values["monto"] = Decimal(str(monto))
    if categoria is not None:
        values["categoria"] = categoria
    if nota is not None:
        values["nota"] = nota

    if not values:
        logger.warning("actualizar_movimiento called with no fields to update")
        return None

    stmt = (
        update(Movement)
        .where(
            Movement.id == movement_id,
            Movement.usuario_id == usuario_id,
        )
        .values(**values)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        logger.warning(
            "IDOR or 404: user=%d tried to update movement_id=%d (no match)",
            usuario_id,
            movement_id,
        )
        return None

    # Fetch the updated row
    refreshed = await db.execute(
        select(Movement).where(Movement.id == movement_id)
    )
    movement = refreshed.scalar_one()

    logger.info(
        "Movement updated: id=%d user=%d fields=%s",
        movement_id,
        usuario_id,
        list(values.keys()),
    )
    await manager.broadcast(usuario_id, "update_dashboard")

    return movement
