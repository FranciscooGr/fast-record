"""
User service — get-or-create pattern.

Always returns a valid User, creating one with default values if
the phone number is not yet registered.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


async def get_or_create_usuario(telefono: str, db: AsyncSession) -> User:
    """
    Look up a user by phone number. If not found, create one with
    sensible defaults and return it.

    This function NEVER raises for a missing user — it auto-creates.

    Parameters
    ----------
    telefono : str
        The unique phone number (e.g. "+5491122334455").
    db : AsyncSession
        The async SQLAlchemy session.

    Returns
    -------
    User
        The existing or newly created User ORM instance.
    """
    stmt = select(User).where(User.telefono == telefono)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        logger.info("User found: id=%d telefono=%s", user.id, telefono)
        return user

    # Auto-create with defaults
    user = User(
        nombre="Usuario",
        apellido="WhatsApp",
        telefono=telefono,
        moneda_principal="ARS",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("User created: id=%d telefono=%s", user.id, telefono)
    return user
