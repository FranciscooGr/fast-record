"""
Movimientos endpoints — CRUD operations on user movements.

Access is keyed by ``public_id`` — no JWT required.

Security:
  - Rate limited (destructive ops).
  - IDOR-safe: every mutation verifies movement ownership via compound
    WHERE (movement.id + movement.usuario_id).  Mismatches return 404
    to avoid leaking ID existence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.services.movimiento_service import (
    actualizar_movimiento,
    eliminar_movimiento,
    resetear_movimientos,
)

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


# ── Pydantic schema for partial updates ─────────────────────────
class MovimientoUpdateRequest(BaseModel):
    """Fields allowed for PATCH-style updates. All optional."""
    tipo: str | None = Field(None, pattern=r"^(INGRESO|EGRESO)$")
    monto: float | None = Field(None, gt=0)
    categoria: str | None = Field(None, max_length=100)
    nota: str | None = Field(None, max_length=500)


async def _resolve_user(public_id: str, db: AsyncSession) -> User:
    """Resolve a user by public_id or raise 404."""
    stmt = select(User).where(User.public_id == public_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── DELETE /movimientos/reset  (wipe all) ───────────────────────
@router.delete("/reset")
@limiter.limit("5/minute")
async def reset_movimientos(
    request: Request,
    public_id: str = Query(..., description="Public ID of the user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete ALL movements for the user identified by public_id,
    effectively resetting their balance to 0.
    """
    user = await _resolve_user(public_id, db)
    deleted = await resetear_movimientos(user.id, db)

    return {
        "message": f"Cuenta reseteada. {deleted} movimientos eliminados.",
        "deleted_count": deleted,
    }


# ── DELETE /movimientos/{movement_id} (single, IDOR-safe) ──────
@router.delete("/{movement_id}")
@limiter.limit("30/minute")
async def delete_movimiento(
    request: Request,
    movement_id: int,
    public_id: str = Query(..., description="Public ID of the user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a single movement by ID.

    IDOR protection: verifies that the movement belongs to the user
    identified by public_id.  Returns 404 for both "not found" and
    "wrong owner" to prevent information leakage.
    """
    user = await _resolve_user(public_id, db)
    success = await eliminar_movimiento(movement_id, user.id, db)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Movimiento no encontrado.",
        )

    return {"message": "Movimiento eliminado.", "deleted_id": movement_id}


# ── PUT /movimientos/{movement_id} (update, IDOR-safe) ─────────
@router.put("/{movement_id}")
@limiter.limit("30/minute")
async def update_movimiento(
    request: Request,
    movement_id: int,
    body: MovimientoUpdateRequest,
    public_id: str = Query(..., description="Public ID of the user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a single movement by ID.

    IDOR protection: same compound WHERE as DELETE.
    Only provided (non-null) fields are patched.
    """
    user = await _resolve_user(public_id, db)
    movement = await actualizar_movimiento(
        movement_id,
        user.id,
        db,
        tipo=body.tipo,
        monto=body.monto,
        categoria=body.categoria,
        nota=body.nota,
    )

    if movement is None:
        raise HTTPException(
            status_code=404,
            detail="Movimiento no encontrado.",
        )

    return {
        "message": "Movimiento actualizado.",
        "movimiento": {
            "id": movement.id,
            "tipo": movement.tipo.value,
            "monto": float(movement.monto),
            "categoria": movement.categoria,
            "nota": movement.nota,
            "fecha": movement.fecha.isoformat(),
        },
    }
