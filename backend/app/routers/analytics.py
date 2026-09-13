from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.services import analytics_service as svc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.compare_periods(db, current_user.property_id, start, end)


@router.get("/channel-mix")
def channel_mix(start: date, end: date, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.channel_mix(db, current_user.property_id, start, end)


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Occupancy/ADR/RevPAR/revenue per calendar month, oldest first — for trend charts."""
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
    return results
