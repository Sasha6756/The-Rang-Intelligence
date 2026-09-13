from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    source_type: Mapped[str] = mapped_column(String(50))  # booking_com/airbnb/direct/reviews/competitors
    filename: Mapped[str] = mapped_column(String(300))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # preview/completed/failed


class ImportMapping(Base):
    """Remembered "your column" -> "system field" mapping per property + source type."""

    __tablename__ = "import_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    source_type: Mapped[str] = mapped_column(String(50))
    column_map: Mapped[dict] = mapped_column(JSON)  # {"Arrival date": "arrival_date", ...}
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
