from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    category: Mapped[str] = mapped_column(String(50))  # pricing/marketing/experience/operations
    severity: Mapped[str] = mapped_column(String(10))  # red/amber/green
    rule_code: Mapped[str] = mapped_column(String(50))

    observation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON)  # the actual computed numbers
    interpretation: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    expected_impact: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(10))  # high/medium/low

    status: Mapped[str] = mapped_column(String(20), default="open")  # open/actioned/dismissed
    target_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OperationalIssue(Base):
    """Phase 2: logged operational issues, present in schema now for forward-compatibility."""

    __tablename__ = "operational_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, default="")
    reported_date: Mapped[date] = mapped_column(Date)
    resolved: Mapped[bool] = mapped_column(default=False)
