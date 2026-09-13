import statistics
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.models.booking import Reservation, ReservationStatus

router = APIRouter(prefix="/api/guests", tags=["guests"])


def _segment_key(r: Reservation) -> str:
    """Simple, explainable rule-based segmentation (not black-box clustering) —
    matches the brief's example segments while staying auditable."""
    if r.lead_time_days >= 45 and r.nights >= 4:
        return "Luxury groups & long-lead planners"
    if r.lead_time_days <= 10 and r.nights <= 3:
        return "Last-minute short stays"
    if r.adults + r.children >= 8:
        return "Large groups & celebrations"
    return "Standard leisure bookings"


@router.get("/segments")
def guest_segments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reservations = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CONFIRMED)
        .all()
    )
    if not reservations:
        return []

    buckets: dict[str, list[Reservation]] = {}
    for r in reservations:
        buckets.setdefault(_segment_key(r), []).append(r)

    total_cancelled_by_seg = {}
    all_res_incl_cancelled = db.query(Reservation).filter(Reservation.property_id == current_user.property_id).all()
    for r in all_res_incl_cancelled:
        seg = _segment_key(r)
        total_cancelled_by_seg.setdefault(seg, [0, 0])
        total_cancelled_by_seg[seg][1] += 1
        if r.status == ReservationStatus.CANCELLED:
            total_cancelled_by_seg[seg][0] += 1

    result = []
    for seg, res_list in buckets.items():
        nights = [r.nights for r in res_list]
        leads = [r.lead_time_days for r in res_list]
        values = [r.gross_revenue for r in res_list]
        cancelled, total = total_cancelled_by_seg.get(seg, [0, len(res_list)])
        result.append({
            "segment": seg,
            "reservation_count": len(res_list),
            "avg_length_of_stay": round(statistics.mean(nights), 1),
            "avg_lead_time_days": round(statistics.mean(leads), 1),
            "avg_booking_value": round(statistics.mean(values), 2),
            "total_revenue": round(sum(values), 2),
            "cancellation_rate_pct": round(cancelled / total * 100, 1) if total else 0,
        })
    return sorted(result, key=lambda s: -s["total_revenue"])


@router.get("/country-mix")
def country_mix(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reservations = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CONFIRMED)
        .all()
    )
    by_country: dict[str, dict] = {}
    for r in reservations:
        country = r.guest.country if r.guest else "Unknown"
        bucket = by_country.setdefault(country, {"country": country, "reservations": 0, "revenue": 0.0})
        bucket["reservations"] += 1
        bucket["revenue"] += r.gross_revenue
    result = list(by_country.values())
    for b in result:
        b["revenue"] = round(b["revenue"], 2)
    return sorted(result, key=lambda b: -b["revenue"])[:15]
