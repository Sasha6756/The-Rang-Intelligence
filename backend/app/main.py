from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.database import engine, Base, SessionLocal
from app.models.core import Channel
import app.models  # noqa: F401  (ensures all models are registered on Base.metadata)
from app.services import currency_service

from app.routers import auth, properties, imports, reservations, analytics, recommendations, reviews, guests, reports, competitors, dashboard, revenue, currency

settings = get_settings()

DEFAULT_CHANNELS = [
    ("Booking.com", 15.0, True),
    ("Airbnb", 3.0, True),
    ("Direct", 0.0, False),
    ("Other", 0.0, True),
]


def seed_channels():
    db = SessionLocal()
    try:
        existing = {c.name for c in db.query(Channel).all()}
        for name, commission, is_ota in DEFAULT_CHANNELS:
            if name not in existing:
                db.add(Channel(name=name, default_commission_pct=commission, is_ota=is_ota))
        db.commit()
    finally:
        db.close()


def refresh_exchange_rates_job():
    """Runs on the daily schedule (and once at startup if today's rate isn't
    in yet) — see currency_service.py for the fetch/store logic. Failures
    are logged, never raised: a missed refresh just means conversions keep
    using the last successful rate until the next attempt succeeds."""
    db = SessionLocal()
    try:
        result = currency_service.refresh_rates(db)
        if not result.get("ok"):
            print(f"[exchange-rates] refresh failed: {result.get('error')} — using last known rates.")
    finally:
        db.close()


scheduler = BackgroundScheduler(timezone="UTC")


def ensure_new_columns():
    """Base.metadata.create_all() only creates tables that don't exist yet —
    it never adds a column to a table that's already there. A database that
    predates a model change (e.g. an existing production Postgres database,
    with real rows already in `properties`) needs that column added
    explicitly, or every query touching it fails with UndefinedColumn.

    This is a minimal, additive-only substitute for a full migration tool:
    it only ever adds a nullable column to a table that already exists, or
    loosens a NOT NULL constraint the current model no longer wants — never
    drops, alters, or touches existing data. New tables (like exchange_rates)
    don't need this; create_all() already handles those."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_columns = [
        ("properties", "default_display_currency", "VARCHAR(10)"),
        ("reservations", "is_calendar_sync", "BOOLEAN DEFAULT FALSE"),
    ]
    for table, column, ddl_type in expected_columns:
        if table not in existing_tables:
            continue
        existing_columns = {c["name"] for c in inspector.get_columns(table)}
        if column in existing_columns:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))

    # A reservation synced from an iCal calendar link has no price at all (the
    # feed format never exposes one) — gross_revenue/net_revenue must accept
    # NULL for those rows. An existing Postgres database created before this
    # was nullable in the model still has the old NOT NULL constraint; this
    # drops it (a no-op if already nullable). Not needed on SQLite: a fresh
    # local/demo database is always created from the current model directly,
    # and SQLite's ALTER TABLE doesn't support this form anyway.
    if engine.dialect.name == "postgresql" and "reservations" in existing_tables:
        with engine.begin() as conn:
            for column in ("gross_revenue", "net_revenue"):
                conn.execute(text(f"ALTER TABLE reservations ALTER COLUMN {column} DROP NOT NULL"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_new_columns()
    seed_channels()
    if settings.SEED_DEMO_DATA:
        from app.seed.demo_data import generate as generate_demo_data
        generate_demo_data()  # idempotent — skips if a demo property already exists

    # Exchange rates: make sure today's rate is in before serving traffic
    # (a brand-new deploy shouldn't wait up to 24h for its first rates), then
    # refresh once a day from then on. A provider outage never blocks
    # startup — refresh_exchange_rates_job() only logs and falls back to
    # whatever rate is already stored.
    db = SessionLocal()
    try:
        status = currency_service.get_status(db)
        needs_refresh = not status["has_data"] or any(v["is_stale"] for v in status["currencies"].values())
    finally:
        db.close()
    if needs_refresh:
        refresh_exchange_rates_job()

    scheduler.add_job(refresh_exchange_rates_job, "cron", hour=1, minute=0, id="daily_fx_refresh", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(imports.router)
app.include_router(reservations.router)
app.include_router(analytics.router)
app.include_router(recommendations.router)
app.include_router(reviews.router)
app.include_router(guests.router)
app.include_router(reports.router)
app.include_router(competitors.router)
app.include_router(dashboard.router)
app.include_router(revenue.router)
app.include_router(currency.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
