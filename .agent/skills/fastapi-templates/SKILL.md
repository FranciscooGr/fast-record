---
name: fastapi-templates
description: Use when starting new FastAPI endpoints, routers, services or project structure. Provides production-ready async patterns, dependency injection and folder layout for ./backend.
---

# FastAPI Templates — Backend Master

## Use this skill when
- Scaffolding new routers or endpoints in `./backend/app/api/v1/`
- Setting up async services in `./backend/app/services/`
- Configuring the FastAPI app in `main.py`
- Implementing dependency injection with `Depends()`
- Setting up lifespan events (startup/shutdown)

## Project Structure
```
./backend/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/     → un archivo por dominio (webhook.py, dashboard.py)
│   │   ├── router.py      → agrega todos los endpoints aquí
│   │   └── deps.py        → dependencias compartidas (get_db, get_current_user)
│   ├── core/
│   │   ├── config.py      → Settings con pydantic-settings
│   │   ├── security.py    → JWT, hashing
│   │   └── logging.py     → structlog setup
│   ├── models/            → SQLAlchemy ORM models
│   ├── schemas/           → Pydantic DTOs (request/response)
│   ├── services/
│   │   ├── whatsapp.py    → webhook handling
│   │   ├── llm_orchestrator.py → Gemini/Groq con fallback
│   │   └── dashboard.py   → lógica de negocio
│   ├── db/
│   │   ├── session.py     → async engine + session
│   │   └── migrations/    → Alembic
│   └── main.py
```

## App Entry Point Pattern
```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.router import api_router
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="Fast Record API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")
```

## Router Pattern
```python
# api/v1/endpoints/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.deps import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await DashboardService.get_summary(db)
```

## Dependency Injection Pattern
```python
# api/v1/deps.py
from app.db.session import AsyncSessionLocal
from app.core.security import verify_token

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)
```

## Settings Pattern
```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    WHATSAPP_VERIFY_TOKEN: str
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

## Do not
- Do not put business logic in endpoint functions — va en `services/`
- Do not use sync functions for I/O — siempre `async def`
- Do not hardcode config values — siempre desde `settings`
- Do not mezclar lógica de presentación con lógica de datos
