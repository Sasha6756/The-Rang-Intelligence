from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.services import analytics_service as svc
from app.services import currency_service as csvc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _apply_display_currency(db: Session, payload, base_currency: str, currency: str | None, rate_mode: str):
    """Every money-bearing endpoint below funnels through this — one
    conversion code path (currency_service.convert_money_in_place) rather
    than bespoke per-endpoint logic. `currency=None` (no display currency
    requested) leaves the response in the property's base currency, as
    before this feature existed."""
    display = (currency or base_currency).upper()
    if display != base_currency.upper():
        csvc.convert_money_in_place(db, payload, base_currency, display, rate_mode)
    return payload


@router.get("/summary")
def summary(
    start: date = Query(...),
    end: date = Query(...),
    currency: str | None = Query(None, description="Display currency (IDR/AUD/USD/EUR). Defaults to the property's base currency."),
    rate_mode: str = Query("current", description="'current' converts at today's rate; 'historical' converts each period at the rate effective on its own dates."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prop = db.get(Property, current_user.property_id)
    result = svc.compare_periods(db, current_user.property_id, start, end)
    return _apply_display_currency(db, result, prop.currency, currency, rate_mode)


@router.get("/channel-mix")
def channel_mix(
    start: date, end: date,
    currency: str | None = Query(None),
    rate_mode: str = Query("current"),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    prop = db.get(Property, current_user.property_id)
    result = svc.channel_mix(db, current_user.property_id, start, end)
    return _apply_display_currency(db, result, prop.currency, currency, rate_mode)


@router.get("/lead-time")
def lead_time(start: date, end: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.lead_time_stats(db, current_user.property_id, start, end)


@router.get("/length-of-stay")
def length_of_stay(start: date, end: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.length_of_stay_stats(db, current_user.property_id, start, end)


@router.get("/cancellations")
def cancellations(start: date, end: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.cancellation_rate(db, current_user.property_id, start, end)


@router.get("/booking-pace")
def pace(
    window_start: date,
    window_end: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.booking_pace(db, current_user.property_id, window_start, window_end)


@router.get("/gaps")
def gaps(
    horizon_days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.find_availability_gaps(db, current_user.property_id, horizon_days)


@router.get("/monthly-trend")
def monthly_trend(
    months: int = 12,
    currency: str | None = Query(None),
    rate_mode: str = Query("current"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Occupancy/ADR/RevPAR/revenue per calendar month, oldest first — for trend charts."""
    prop = db.get(Property, current_user.property_id)
    today = date.today()
    results = []
    y, m = today.year, today.month
    cursor_months = []
    for i in range(months - 1, -1, -1):
        idx = (y * 12 + (m - 1)) - i
        yy, mm = divmod(idx, 12)
        cursor_months.append((yy, mm + 1))
    for yy, mm in cursor_months:
        start = date(yy, mm, 1)
        end = date(yy + 1, 1, 1) if mm == 12 else date(yy, mm + 1, 1)
        metrics = svc.core_metrics(db, current_user.property_id, start, end)
        results.append({"month": start.strftime("%Y-%m"), **metrics})
    return _apply_display_currency(db, results, prop.currency, currency, rate_mode)
