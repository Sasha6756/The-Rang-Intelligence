from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.models.booking import Reservation, ReservationStatus
from app.models.recommendation import Recommendation
from app.services import analytics_service as asvc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/today")
def today(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prop = db.get(Property, current_user.property_id)
    today_date = date.today()

    current = asvc.core_metrics(db, current_user.property_id, today_date, today_date + timedelta(days=1))
    next_30 = asvc.core_metrics(db, current_user.property_id, today_date, today_date + timedelta(days=30))

    next_arrival = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CONFIRMED, Reservation.arrival_date >= today_date)
        .order_by(Reservation.arrival_date)
        .first()
    )
    next_departure = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CONFIRMED, Reservation.departure_date >= today_date)
        .order_by(Reservation.departure_date)
        .first()
    )

    recent_bookings = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.booking_date >= today_date - timedelta(days=7))
        .order_by(Reservation.booking_date.desc())
        .limit(10)
        .all()
    )
    recent_cancellations = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CANCELLED, Reservation.cancellation_date >= today_date - timedelta(days=14))
        .all()
    )

    gaps = asvc.find_availability_gaps(db, current_user.property_id, horizon_days=30, min_gap_nights=1)
    upcoming_empty_nights = sum(g["nights"] for g in gaps)

    open_recs = (
        db.query(Recommendation)
        .filter(Recommendation.property_id == current_user.property_id, Recommendation.status == "open")
        .order_by(Recommendation.severity.desc(), Recommendation.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        "property_name": prop.name,
        "target_occupancy_pct": prop.target_occupancy_pct,
        "target_adr": prop.target_adr,
        "currency": prop.currency,
        "current_occupancy_today_pct": current["occupancy_pct"],
        "next_30_days_occupancy_pct": next_30["occupancy_pct"],
        "next_30_days_revenue": next_30["gross_revenue"],
        "current_adr_trailing": next_30["adr"],
        "upcoming_empty_nights_30d": upcoming_empty_nights,
        "next_arrival": None if not next_arrival else {"date": next_arrival.arrival_date, "guest_country": next_arrival.guest.country if next_arrival.guest else None, "nights": next_arrival.nights},
        "next_departure": None if not next_departure else {"date": next_departure.departure_date},
        "recent_bookings_count_7d": len(recent_bookings),
        "recent_cancellations_count_14d": len(recent_cancellations),
        "actions": [
            {
                "id": r.id, "category": r.category, "severity": r.severity,
                "observation": r.observation, "interpretation": r.interpretation,
                "action": r.action, "expected_impact": r.expected_impact, "confidence": r.confidence,
            }
            for r in open_recs
        ],
    }
