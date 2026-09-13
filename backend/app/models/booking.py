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

    gross_revenue: Mapped[float] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    net_revenue: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.CONFIRMED)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    source_detail: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["Channel"] = relationship()
    guest: Mapped["Guest"] = relationship()

    @property
    def adr(self) -> float:
        return round(self.gross_revenue / self.nights, 2) if self.nights else 0.0

    @property
    def lead_time_days(self) -> int:
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
