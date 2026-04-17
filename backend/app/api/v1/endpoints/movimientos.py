"""
Movimientos endpoints — destructive operations on user movements.

Access is keyed by ``public_id`` — no JWT required.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.models.user import User
from app.services.movimiento_service import resetear_movimientos

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.delete("/reset")
async def reset_movimientos(
    public_id: str = Query(..., description="Public ID of the user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete ALL movements for the user identified by public_id,
    effectively resetting their balance to 0.
    """
    stmt = select(User).where(User.public_id == public_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    deleted = await resetear_movimientos(user.id, db)

    return {
        "message": f"Cuenta reseteada. {deleted} movimientos eliminados.",
        "deleted_count": deleted,
    }
