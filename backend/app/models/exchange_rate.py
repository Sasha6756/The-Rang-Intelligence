from datetime import date, datetime

from sqlalchemy import String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExchangeRate(Base):
    """One row per (base_currency, quote_currency, effective_date).

    Rows are never overwritten with a new effective_date's data — a fresh
    daily fetch inserts a new row, so history is retained for historical-rate
    conversions and rate-movement reporting (see docs/ARCHITECTURE.md
    section 11.3). Re-fetching the *same* effective_date (e.g. an extra
    manual refresh the same day) updates that one row in place rather than
    duplicating it.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("base_currency", "quote_currency", "effective_date", name="uq_exchange_rate_pair_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    quote_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[float] = mapped_column(Float)  # quote-currency units per 1 base-currency unit
    source: Mapped[str] = mapped_column(String(100), default="")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
