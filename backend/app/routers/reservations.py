from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.models.booking import Reservation, ReservationStatus
from app.services import currency_service as csvc

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


@router.get("")
def list_reservations(
    start: date | None = None,
    end: date | None = None,
    status: str | None = None,
    currency: str | None = Query(None),
    rate_mode: str = Query("current"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Reservation).filter(Reservation.property_id == current_user.property_id)
    if start:
        q = q.filter(Reservation.departure_date >= start)
    if end:
        q = q.filter(Reservation.arrival_date <= end)
    if status:
        q = q.filter(Reservation.status == status)
    reservations = q.order_by(Reservation.arrival_date).all()

    result = [
        {
            "id": r.id,
            "channel_name": r.channel.name if r.channel else "Unknown",
            "guest_country": r.guest.country if r.guest else None,
            "external_ref": r.external_ref,
            "booking_date": r.booking_date,
            "arrival_date": r.arrival_date,
            "departure_date": r.departure_date,
            "nights": r.nights,
            "adults": r.adults,
            "children": r.children,
            "gross_revenue": r.gross_revenue,
            "commission": r.commission,
            "net_revenue": r.net_revenue,
            "adr": r.adr,
            "lead_time_days": r.lead_time_days,
            "currency": r.currency,
            "status": r.status.value,
            "is_calendar_sync": r.is_calendar_sync,
            # Captured before any conversion below — the amount and currency exactly
            # as stored on the reservation record. Never overwritten, regardless of
            # which display currency was requested; shown in the UI so a viewer can
            # always see the true original transaction figure alongside the converted one.
            "original_amount": r.gross_revenue,
            "original_currency": r.currency,
        }
        for r in reservations
    ]

    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, result, prop.currency, display, rate_mode)
        for row in result:
            row["currency"] = display  # the per-row original currency is superseded by the requested display currency
            # original_amount/original_currency intentionally left untouched by conversion
    return result


@router.get("/calendar")
def calendar_view(
    start: date = Query(...),
    end: date = Query(...),
    currency: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservations = (
        db.query(Reservation)
        .filter(
            Reservation.property_id == current_user.property_id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.arrival_date < end,
            Reservation.departure_date > start,
        )
        .all()
    )

    days = {}
    cur = start
    while cur < end:
        days[cur] = {"date": cur, "is_booked": False, "adr": None, "guest_country": None}
        cur += timedelta(days=1)

    for r in reservations:
        cur = max(r.arrival_date, start)
        stop = min(r.departure_date, end)
        while cur < stop:
            if cur in days:
                days[cur].update(is_booked=True, adr=r.adr, guest_country=r.guest.country if r.guest else None)
            cur += timedelta(days=1)

    result = list(days.values())
    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, result, prop.currency, display, "current")
    return result
