"""
Movimientos endpoints — destructive operations on user movements.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_current_user
from app.services.movimiento_service import resetear_movimientos

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.delete("/reset")
async def reset_movimientos(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete ALL movements for the authenticated user, effectively
    resetting their balance to 0.

    Requires JWT Bearer authentication.
    """
    try:
        user_id = int(current_user["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    deleted = await resetear_movimientos(user_id, db)

    return {
        "message": f"Cuenta reseteada. {deleted} movimientos eliminados.",
        "deleted_count": deleted,
    }
