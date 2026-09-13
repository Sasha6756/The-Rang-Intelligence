from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ICalFeed(Base):
    """A saved Airbnb/Booking.com calendar-export URL for a property, so the
    user pastes it once and future syncs just re-fetch it."""

    __tablename__ = "ical_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    url: Mapped[str] = mapped_column(String(2000))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str] = mapped_column(String(20), default="never")  # never/ok/error
    last_sync_message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    channel: Mapped["Channel"] = relationship()


from app.models.core import Channel  # noqa: E402
