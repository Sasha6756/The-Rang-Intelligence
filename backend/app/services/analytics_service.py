"""
Deterministic analytics — every number here is arithmetic over the database,
never an LLM guess. See docs/ARCHITECTURE.md section 6 for the formulas.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.booking import Reservation, ReservationStatus
from app.models.core import Channel


def _confirmed(db: Session, property_id: int):
    return db.query(Reservation).filter(
        Reservation.property_id == property_id,
        Reservation.status == ReservationStatus.CONFIRMED,
    )


def _nights_overlap(res: Reservation, start: date, end: date) -> int:
    a, d = max(res.arrival_date, start), min(res.departure_date, end)
    return max((d - a).days, 0)


def core_metrics(db: Session, property_id: int, start: date, end: date) -> dict:
    """Occupancy, ADR, RevPAR, gross/net revenue for [start, end).

    Occupancy counts every booked night regardless of source. ADR/RevPAR/
    revenue, however, can only be computed from nights with a known price —
    a reservation synced from an iCal calendar link has no price at all, so
    it contributes to occupancy but is excluded from the money figures
    rather than being treated as $0 (which would silently understate ADR).
    `unpriced_nights` tells the caller how many booked nights were excluded
    this way, so the UI can flag it instead of presenting a clean number.
    """
    available_nights = max((end - start).days, 0)
    reservations = [
        r for r in _confirmed(db, property_id)
        .filter(Reservation.arrival_date < end, Reservation.departure_date > start)
        .all()
    ]

    booked_nights = 0
    priced_nights = 0
    gross = 0.0
    net = 0.0
    for r in reservations:
        n = _nights_overlap(r, start, end)
        booked_nights += n
        if r.gross_revenue is not None and r.nights:
            share = n / r.nights
            gross += r.gross_revenue * share
            net += (r.net_revenue or 0.0) * share
            priced_nights += n

    occupancy_pct = round(booked_nights / available_nights * 100, 1) if available_nights else 0.0
    adr = round(gross / priced_nights, 2) if priced_nights else None
    revpar = round(gross / available_nights, 2) if available_nights and priced_nights else None

    return {
        "start": start, "end": end,
        "available_nights": available_nights,
        "booked_nights": booked_nights,
        "unpriced_nights": booked_nights - priced_nights,
        "occupancy_pct": occupancy_pct,
        "adr": adr,
        "revpar": revpar,
        "gross_revenue": round(gross, 2),
        "net_revenue": round(net, 2),
        "reservation_count": len(reservations),
    }


def compare_periods(db: Session, property_id: int, start: date, end: date) -> dict:
    """current vs. previous-equal-length period, vs. same period last year, vs. trailing historical average."""
    length = (end - start).days
    prev_start, prev_end = start - timedelta(days=length), start
    yoy_start, yoy_end = start.replace(year=start.year - 1), end.replace(year=end.year - 1)

    current = core_metrics(db, property_id, start, end)
    previous_period = core_metrics(db, property_id, prev_start, prev_end)

    try:
        same_period_last_year = core_metrics(db, property_id, yoy_start, yoy_end)
    except ValueError:
        same_period_last_year = None

    # trailing historical average occupancy, using up to the last 365 days before `start`
    hist_start = start - timedelta(days=365)
    historical = core_metrics(db, property_id, hist_start, start) if hist_start < start else None

    return {
        "current": current,
        "previous_period": previous_period,
        "same_period_last_year": same_period_last_year,
        "trailing_365d_average": historical,
    }


def channel_mix(db: Session, property_id: int, start: date, end: date) -> list[dict]:
    reservations = _confirmed(db, property_id).filter(
        Reservation.arrival_date < end, Reservation.departure_date > start
    ).all()
    by_channel: dict[str, dict] = {}
    total_gross = 0.0
    for r in reservations:
        name = r.channel.name if r.channel else "Unknown"
        bucket = by_channel.setdefault(
            name, {"channel": name, "reservations": 0, "unpriced_reservations": 0,
                   "gross_revenue": 0.0, "net_revenue": 0.0, "nights": 0}
        )
        bucket["reservations"] += 1
        bucket["nights"] += r.nights
        if r.gross_revenue is None:
            bucket["unpriced_reservations"] += 1
        else:
            bucket["gross_revenue"] += r.gross_revenue
            bucket["net_revenue"] += r.net_revenue or 0.0
            total_gross += r.gross_revenue

    result = list(by_channel.values())
    for b in result:
        b["revenue_share_pct"] = round(b["gross_revenue"] / total_gross * 100, 1) if total_gross else 0.0
        b["gross_revenue"] = round(b["gross_revenue"], 2)
        b["net_revenue"] = round(b["net_revenue"], 2)
    return sorted(result, key=lambda b: -b["gross_revenue"])


def lead_time_stats(db: Session, property_id: int, start: date, end: date) -> dict:
    # Calendar-synced reservations (from an Airbnb/Booking iCal link) have no
    # real booking_date — the feed only exposes stay dates — so they're
    # excluded here rather than skewing lead time with a fabricated value.
    reservations = _confirmed(db, property_id).filter(
        Reservation.booking_date >= start, Reservation.booking_date < end,
        Reservation.is_calendar_sync.is_(False),
    ).all()
    lead_times = [r.lead_time_days for r in reservations if r.lead_time_days is not None]
    if not lead_times:
        return {"count": 0, "mean_days": None, "median_days": None}
    return {
        "count": len(lead_times),
        "mean_days": round(statistics.mean(lead_times), 1),
        "median_days": round(statistics.median(lead_times), 1),
        "min_days": min(lead_times),
        "max_days": max(lead_times),
    }


def length_of_stay_stats(db: Session, property_id: int, start: date, end: date) -> dict:
    reservations = _confirmed(db, property_id).filter(
        Reservation.arrival_date >= start, Reservation.arrival_date < end
    ).all()
    nights = [r.nights for r in reservations]
    if not nights:
        return {"count": 0, "mean_nights": None, "median_nights": None, "distribution": {}}
    distribution: dict[int, int] = {}
    for n in nights:
        distribution[n] = distribution.get(n, 0) + 1
    return {
        "count": len(nights),
        "mean_nights": round(statistics.mean(nights), 1),
        "median_nights": round(statistics.median(nights), 1),
        "distribution": dict(sorted(distribution.items())),
    }


def cancellation_rate(db: Session, property_id: int, start: date, end: date) -> dict:
    # Same reasoning as lead_time_stats: calendar-synced rows have no real
    # booking_date, so they're excluded rather than misplaced in the window.
    all_res = db.query(Reservation).filter(
        Reservation.property_id == property_id,
        Reservation.booking_date >= start, Reservation.booking_date < end,
        Reservation.is_calendar_sync.is_(False),
    ).all()
    if not all_res:
        return {"total": 0, "cancelled": 0, "rate_pct": None}
    cancelled = sum(1 for r in all_res if r.status == ReservationStatus.CANCELLED)
    return {"total": len(all_res), "cancelled": cancelled, "rate_pct": round(cancelled / len(all_res) * 100, 1)}


def booking_pace(db: Session, property_id: int, window_start: date, window_end: date, as_of: date | None = None) -> dict:
    """
    Compares how fully `[window_start, window_end)` is currently booked
    against how fully comparable historical windows were booked at the same
    lead time. See docs/ARCHITECTURE.md section 6/8.
    """
    as_of = as_of or date.today()
    days_out = (window_start - as_of).days
    available_nights = max((window_end - window_start).days, 0)
    if available_nights <= 0 or days_out < 0:
        return {"error": "window must be in the future", "days_out": days_out}

    current_booked = sum(
        _nights_overlap(r, window_start, window_end)
        for r in _confirmed(db, property_id)
        .filter(Reservation.booking_date <= as_of, Reservation.arrival_date < window_end, Reservation.departure_date > window_start)
        .all()
    )
    current_pct = round(current_booked / available_nights * 100, 1)

    # historical comparables: same-length windows starting on the same day-of-year
    # in prior years (seasonality), evaluated at the same lead time. Falls back to
    # "insufficient data" rather than guessing if none exist.
    samples = []
    for years_back in (1, 2, 3):
        try:
            h_start = window_start.replace(year=window_start.year - years_back)
        except ValueError:
            continue
        h_end = h_start + timedelta(days=available_nights)
        h_as_of = h_start - timedelta(days=days_out)
        if h_end > date.today():
            continue  # that historical window hasn't fully happened yet — not comparable
        h_booked = sum(
            _nights_overlap(r, h_start, h_end)
            for r in _confirmed(db, property_id)
            .filter(Reservation.booking_date <= h_as_of, Reservation.arrival_date < h_end, Reservation.departure_date > h_start)
            .all()
        )
        h_nights = max((h_end - h_start).days, 0)
        if h_nights:
            samples.append(h_booked / h_nights * 100)

    if not samples:
        return {
            "days_out": days_out, "current_pct": current_pct,
            "historical_pct": None, "sample_size": 0,
            "label": "insufficient_data",
            "message": "Insufficient historical data to compare booking pace for this window.",
        }

    historical_pct = round(statistics.mean(samples), 1)
    delta = current_pct - historical_pct
    label = "slower" if delta < -8 else ("faster" if delta > 8 else "normal")
    return {
        "days_out": days_out, "current_pct": current_pct,
        "historical_pct": historical_pct, "sample_size": len(samples),
        "delta_pts": round(delta, 1), "label": label,
    }


def find_availability_gaps(db: Session, property_id: int, horizon_days: int = 90, min_gap_nights: int = 2) -> list[dict]:
    """Upcoming stretches of consecutive unbooked nights within the horizon."""
    today = date.today()
    horizon_end = today + timedelta(days=horizon_days)
    reservations = _confirmed(db, property_id).filter(
        Reservation.arrival_date < horizon_end, Reservation.departure_date > today
    ).all()
    booked_dates: set[date] = set()
    for r in reservations:
        d = max(r.arrival_date, today)
        stop = min(r.departure_date, horizon_end)
        while d < stop:
            booked_dates.add(d)
            d += timedelta(days=1)

    gaps = []
    d = today
    gap_start = None
    while d < horizon_end:
        if d not in booked_dates:
            if gap_start is None:
                gap_start = d
        else:
            if gap_start is not None and (d - gap_start).days >= min_gap_nights:
                gaps.append({"start": gap_start, "end": d, "nights": (d - gap_start).days})
            gap_start = None
        d += timedelta(days=1)
    if gap_start is not None and (horizon_end - gap_start).days >= min_gap_nights:
        gaps.append({"start": gap_start, "end": horizon_end, "nights": (horizon_end - gap_start).days})

    return gaps


def competitor_median_rate(db, property_id: int, start: date, end: date):
    from app.models.competitor import Competitor, CompetitorRate
    rates = (
        db.query(CompetitorRate.nightly_rate)
        .join(Competitor, Competitor.id == CompetitorRate.competitor_id)
        .filter(Competitor.property_id == property_id, CompetitorRate.date >= start, CompetitorRate.date < end, CompetitorRate.nightly_rate.isnot(None))
        .all()
    )
    values = [r[0] for r in rates]
    if len(values) < 3:
        return {"median_rate": None, "sample_size": len(values), "message": "Insufficient competitor data (need at least 3 rate observations)."}
    return {"median_rate": round(statistics.median(values), 2), "sample_size": len(values)}


def competitor_availability(db, property_id: int, start: date, end: date):
    from app.models.competitor import Competitor, CompetitorRate
    rows = (
        db.query(CompetitorRate.available)
        .join(Competitor, Competitor.id == CompetitorRate.competitor_id)
        .filter(Competitor.property_id == property_id, CompetitorRate.date >= start, CompetitorRate.date < end)
        .all()
    )
    if len(rows) < 3:
        return {"available_pct": None, "sample_size": len(rows), "message": "Insufficient competitor data."}
    available = sum(1 for r in rows if r[0])
    return {"available_pct": round(available / len(rows) * 100, 1), "sample_size": len(rows)}
