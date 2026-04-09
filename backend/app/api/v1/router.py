"""
Central API v1 router — aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.simulador import router as simulador_router
from app.api.v1.endpoints.usuarios import router as usuarios_router
from app.api.v1.endpoints.webhook import router as webhook_router

api_router = APIRouter()

# ── Simulador (development only) ───────────────────────────
api_router.include_router(simulador_router)

# ── Usuarios ────────────────────────────────────────────────
api_router.include_router(usuarios_router)

# ── WhatsApp Webhook ────────────────────────────────────────
api_router.include_router(webhook_router)

# ── Register domain routers here as the project grows ───────
from app.api.v1.endpoints.dashboard import router as dashboard_router
api_router.include_router(dashboard_router)

# ── Movimientos (reset, etc.) ──────────────────────────────
from app.api.v1.endpoints.movimientos import router as movimientos_router
api_router.include_router(movimientos_router)

