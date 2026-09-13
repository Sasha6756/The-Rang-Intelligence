import enum
from datetime import date, datetime

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ReservationStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    name: Mapped[str] = mapped_column(String(200))
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    guest_id: Mapped[int | None] = mapped_column(ForeignKey("guests.id"), nullable=True)
    promotion_id: Mapped[int | None] = mapped_column(ForeignKey("promotions.id"), nullable=True)
    imported_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)

    external_ref: Mapped[str] = mapped_column(String(200), default="")
    booking_date: Mapped[date] = mapped_column(Date)
    arrival_date: Mapped[date] = mapped_column(Date)
    departure_date: Mapped[date] = mapped_column(Date)
    nights: Mapped[int] = mapped_column(Integer)
    adults: Mapped[int] = mapped_column(Integer, default=2)
    children: Mapped[int] = mapped_column(Integer, default=0)

    # Nullable: a reservation synced from an iCal calendar link (Airbnb/Booking
    # only export date ranges, not price) has no revenue figure. Analytics
    # code must treat None as "unknown" and exclude it from ADR/RevPAR/revenue
    # sums rather than treating it as zero — see analytics_service.py.
    gross_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    net_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # True when booking_date (and therefore lead_time_days) is not a real,
    # known value — set for records created from an iCal calendar sync
    # (which never exposes a booking date) and for records backfilled from a
    # revenue/payout report with no matching booking (same limitation).
    # These rows have real arrival/departure dates, so they count toward
    # occupancy, length-of-stay and channel mix; analytics that depend on
    # booking_date — lead time, booking pace, cancellation rate — exclude
    # them rather than compute a misleading number from a fallback date.
    is_calendar_sync: Mapped[bool] = mapped_column(Boolean, default=False)

    source_detail: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["Channel"] = relationship()
    guest: Mapped["Guest"] = relationship()

    @property
    def adr(self) -> float | None:
        if not self.nights or self.gross_revenue is None:
            return None
        return round(self.gross_revenue / self.nights, 2)

    @property
    def lead_time_days(self) -> int | None:
        if self.is_calendar_sync:
            return None  # booking_date is a sync-time placeholder, not real
        return (self.arrival_date - self.booking_date).days


class CalendarDay(Base):
    """One row per property per date; derived/maintained alongside reservations."""

    __tablename__ = "calendar_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    date: Mapped[date] = mapped_column(Date)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stay: Mapped[int] = mapped_column(Integer, default=1)
    note: Mapped[str] = mapped_column(String(300), default="")


# import at bottom to avoid circulars while keeping relationship() typed above
from app.models.core import Channel, Guest  # noqa: E402
