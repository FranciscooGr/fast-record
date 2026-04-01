"""
Application settings — loaded from .env, never hardcoded.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/fast_record"

    # ── JWT ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── WhatsApp ────────────────────────────────────────────────
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_API_TOKEN: str = ""

    # ── LLM Providers ───────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
