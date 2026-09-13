"""
Application settings, loaded from environment variables (.env in local dev).

Nothing secret is hard-coded. DATABASE_URL defaults to a local SQLite file so
the product runs with zero external services; point it at a Postgres DSN in
production (see README.md / docker-compose.yml).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "The Rang Intelligence"
    ENVIRONMENT: str = "local"

    # Default: zero-config local SQLite file. Set DATABASE_URL to a Postgres
    # DSN (e.g. postgresql+psycopg2://user:pass@host:5432/rang) in production.
    DATABASE_URL: str = "sqlite:///./rang_intelligence.db"

    # JWT auth
    SECRET_KEY: str = "dev-only-secret-change-me"  # override in .env for any non-local use
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Optional: enables LLM-backed narrative generation. When unset, the
    # deterministic template narrator is used instead — the product is fully
    # functional either way.
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # If true, populates the demo dataset on startup when the database is
    # empty. Safe to leave on — it's a no-op once a property already exists.
    SEED_DEMO_DATA: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
