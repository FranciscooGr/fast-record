"""
Test fixtures for Fast Record backend.

Uses httpx.AsyncClient + ASGITransport to hit the FastAPI app
without spinning up a real server.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client that talks directly to the ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
