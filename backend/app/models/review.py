from datetime import date

from sqlalchemy import String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    source: Mapped[str] = mapped_column(String(50), default="Direct")  # Booking.com/Airbnb/Google/Direct
    review_date: Mapped[date] = mapped_column(Date)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # normalised 0-100 where possible
    guest_country: Mapped[str] = mapped_column(String(100), default="Unknown")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)  # -1..+1


class ReviewTopic(Base):
    """One row per (review, topic) mention, produced by the review_sentiment service."""

    __tablename__ = "review_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"))
    topic: Mapped[str] = mapped_column(String(50))
    sentiment: Mapped[str] = mapped_column(String(10))  # positive/negative/neutral
    snippet: Mapped[str] = mapped_column(String(500), default="")
