"""
Phase 2/3 tables named in the brief (expenses, campaigns, guest_messages).

Present in the schema for forward-compatibility so future work doesn't
require a breaking migration, but not populated or surfaced by the MVP UI —
see docs/ARCHITECTURE.md section 5 for what's actually built.
"""
from datetime import date

from sqlalchemy import String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(String(500), default="")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(100), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    clicks: Mapped[int] = mapped_column(default=0)
    enquiries: Mapped[int] = mapped_column(default=0)
    bookings: Mapped[int] = mapped_column(default=0)
    attributed_revenue: Mapped[float] = mapped_column(Float, default=0.0)


class GuestMessage(Base):
    __tablename__ = "guest_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[date | None] = mapped_column(Date, nullable=True)
