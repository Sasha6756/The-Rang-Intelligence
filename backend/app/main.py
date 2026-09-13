from contextlib import asynccontextmanager

from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import engine, Base, SessionLocal
from app.models.core import Channel
import app.models  # noqa: F401  (ensures all models are registered on Base.metadata)

from app.routers import auth, properties, imports, reservations, analytics, recommendations, reviews, guests, reports, competitors, dashboard

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_channels()
    yield


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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
