"""
FastAPI application entry point.

Lifespan manages startup/shutdown:
- Startup: initialise logging
- Shutdown: dispose the async engine connection pool
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.db.session import engine

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    setup_logging()
    yield
    # ── Shutdown ─────────────────────────────────────────────
    await engine.dispose()


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Fast Record API",
    description="Financial record-keeping backend for WhatsApp-driven expense tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["infra"])
async def health_check():
    return {"status": "ok"}
