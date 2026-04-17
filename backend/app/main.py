"""
FastAPI application entry point.

Lifespan manages startup/shutdown:
- Startup: initialise logging
- Shutdown: dispose the async engine connection pool
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.db.session import Base, engine
from app.models.user import User  # noqa: F401
from app.models.movement import Movement  # noqa: F401

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.getLogger(__name__).info("Database tables created / verified.")
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

# ── Rate Limiting ───────────────────────────────────────────────
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


async def _custom_rate_limit_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return a clean JSON 429 instead of the default HTML error."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Intentá de nuevo en un momento.",
            "retry_after": exc.detail,
        },
    )


app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)

# ── CORS ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://fast-record.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["infra"])
async def health_check():
    return {"status": "ok"}
