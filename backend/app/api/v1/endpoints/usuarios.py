"""
User endpoints — GET /api/v1/usuarios/{telefono}
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db
from app.services.usuario_service import get_or_create_usuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


# ── Response schema ─────────────────────────────────────────────
class UsuarioResponse(BaseModel):
    """Public representation of a User."""

    id: int
    nombre: str
    apellido: str
    telefono: str
    moneda_principal: str

    model_config = {"from_attributes": True}


# ── Endpoint ────────────────────────────────────────────────────
@router.get(
    "/{telefono}",
    response_model=UsuarioResponse,
    summary="Get or create a user by phone number",
    description=(
        "Looks up the user by phone. If not found, creates one with "
        "default values (nombre='Usuario', apellido='WhatsApp', moneda='ARS')."
    ),
)
async def get_usuario_por_telefono(
    telefono: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the user for the given phone number, creating if needed."""
    user = await get_or_create_usuario(telefono, db)
    return user
