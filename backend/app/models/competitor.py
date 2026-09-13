from datetime import date

from sqlalchemy import String, Integer, Float, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    name: Mapped[str] = mapped_column(String(200))
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(200), default="Uluwatu")
    has_pool: Mapped[bool] = mapped_column(Boolean, default=True)
    has_sauna: Mapped[bool] = mapped_column(Boolean, default=False)
    ocean_view: Mapped[bool] = mapped_column(Boolean, default=True)
    review_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    listing_url: Mapped[str] = mapped_column(String(500), default="")
    notes: Mapped[str] = mapped_column(String(1000), default="")


class CompetitorRate(Base):
    """Manually entered / CSV-imported competitor rate observations.

    Not scraped live — see architecture doc section 3/33 on data sourcing.
    """

    __tablename__ = "competitor_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"))
    date: Mapped[date] = mapped_column(Date)
    nightly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stay: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(50), default="manual")
