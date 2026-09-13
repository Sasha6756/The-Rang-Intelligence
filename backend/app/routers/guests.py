import statistics
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.models.booking import Reservation, ReservationStatus
from app.services import currency_service as csvc

router = APIRouter(prefix="/api/guests", tags=["guests"])


def _segment_key(r: Reservation) -> str:
    """Simple, explainable rule-based segmentation (not black-box clustering) —
    matches the brief's example segments while staying auditable. Calendar-
    synced reservations have no real lead_time_days, so they skip the
    lead-time-based rules rather than being scored against a fabricated
    value, and fall through to the party-size/default rules."""
    if r.lead_time_days is not None:
        if r.lead_time_days >= 45 and r.nights >= 4:
            return "Luxury groups & long-lead planners"
        if r.lead_time_days <= 10 and r.nights <= 3:
            return "Last-minute short stays"
    if r.adults + r.children >= 8:
        return "Large groups & celebrations"
    return "Standard leisure bookings"


@router.get("/segments")
def guest_segments(
    currency: str | None = Query(None),
    rate_mode: str = Query("current"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        # Calendar-synced reservations have no known lead time or price —
        # excluded from these averages (rather than treated as 0/None-in-mean)
        # so a mix of priced and unpriced bookings doesn't skew the numbers.
        nights = [r.nights for r in res_list]
        leads = [r.lead_time_days for r in res_list if r.lead_time_days is not None]
        values = [r.gross_revenue for r in res_list if r.gross_revenue is not None]
        cancelled, total = total_cancelled_by_seg.get(seg, [0, len(res_list)])
        result.append({
            "segment": seg,
            "reservation_count": len(res_list),
            "unpriced_reservation_count": len(res_list) - len(values),
            "avg_length_of_stay": round(statistics.mean(nights), 1) if nights else None,
            "avg_lead_time_days": round(statistics.mean(leads), 1) if leads else None,
            "avg_booking_value": round(statistics.mean(values), 2) if values else None,
            "total_revenue": round(sum(values), 2),
            "cancellation_rate_pct": round(cancelled / total * 100, 1) if total else 0,
        })
    result = sorted(result, key=lambda s: -s["total_revenue"])

    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, result, prop.currency, display, rate_mode)
    return result


@router.get("/country-mix")
def country_mix(
    currency: str | None = Query(None),
    rate_mode: str = Query("current"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservations = (
        db.query(Reservation)
        .filter(Reservation.property_id == current_user.property_id, Reservation.status == ReservationStatus.CONFIRMED)
        .all()
    )
    by_country: dict[str, dict] = {}
    for r in reservations:
        country = r.guest.country if r.guest else "Unknown"
        bucket = by_country.setdefault(country, {"country": country, "reservations": 0, "revenue": 0.0, "unpriced_reservations": 0})
        bucket["reservations"] += 1
        if r.gross_revenue is None:
            bucket["unpriced_reservations"] += 1
        else:
            bucket["revenue"] += r.gross_revenue
    result = list(by_country.values())
    for b in result:
        b["revenue"] = round(b["revenue"], 2)
    result = sorted(result, key=lambda b: -b["revenue"])[:15]

    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, result, prop.currency, display, rate_mode)
    return result
