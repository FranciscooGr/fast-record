"""
Shared dependencies for API v1 endpoints.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import AsyncSessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Yield an async DB session, auto-closed on exit."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode and validate the JWT Bearer token."""
    return verify_token(token)
