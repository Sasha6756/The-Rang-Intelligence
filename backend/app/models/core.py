import enum
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="The Rang Uluwatu")
    address: Mapped[str] = mapped_column(String(300), default="Uluwatu, Bali, Indonesia")
    bedrooms: Mapped[int] = mapped_column(Integer, default=5)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Makassar")
    target_occupancy_pct: Mapped[float] = mapped_column(Float, default=65.0)
    target_adr: Mapped[float] = mapped_column(Float, default=1450.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="property")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.OWNER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    property: Mapped["Property"] = relationship(back_populates="users")


class Channel(Base):
    """Booking.com / Airbnb / Direct / Other."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    default_commission_pct: Mapped[float] = mapped_column(Float, default=0.0)
    is_ota: Mapped[bool] = mapped_column(Boolean, default=True)


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    name: Mapped[str] = mapped_column(String(200), default="")
    country: Mapped[str] = mapped_column(String(100), default="Unknown")
    is_repeat: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(String(1000), default="")
