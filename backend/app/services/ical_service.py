"""
Sync reservations from an Airbnb/Booking.com iCal calendar-export link.

These feeds only expose date ranges (arrival/departure) — never price, guest
name, or the true date a booking was made. That's a hard limitation of the
format, not something we work around by guessing: records created here are
flagged `is_calendar_sync=True` so analytics_service excludes them from
ADR/RevPAR/lead-time/booking-pace/cancellation-rate, while still counting
them toward occupancy, length-of-stay and channel mix.
"""
from __future__ import annotations

from datetime import date, datetime

import httpx
from icalendar import Calendar
from sqlalchemy.orm import Session

from app.models.booking import Reservation, ReservationStatus
from app.models.ical_feed import ICalFeed
from app.services.import_service import get_or_create_channel

MAX_FEED_BYTES = 5 * 1024 * 1024  # 5MB — generous for a calendar feed, guards against abuse


class ICalSyncError(Exception):
    """Any user-facing sync failure (bad URL, network error, unparseable feed)."""


def _as_date(value) -> date:
    """icalendar gives DTSTART/DTEND as date or datetime depending on the feed."""
    if isinstance(value, datetime):
        return value.date()
    return value


def _fetch(url: str) -> bytes:
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ICalSyncError("That doesn't look like a valid link — it should start with https://")
    try:
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            resp = client.get(url)
    except httpx.TimeoutException:
        raise ICalSyncError("The calendar link timed out. Please check the URL and try again.")
    except httpx.HTTPError as e:
        raise ICalSyncError(f"Could not reach that calendar link ({e.__class__.__name__}).")

    if resp.status_code != 200:
        raise ICalSyncError(
            f"The calendar link returned an error (HTTP {resp.status_code}). "
            "It may have expired — copy a fresh export link from Airbnb/Booking.com."
        )
    if len(resp.content) > MAX_FEED_BYTES:
        raise ICalSyncError("That file is unexpectedly large for a calendar export — please double-check the URL.")
    return resp.content


def _parse(content: bytes) -> list[dict]:
    try:
        cal = Calendar.from_ical(content)
    except Exception:
        raise ICalSyncError("That link didn't return a valid calendar (.ics) file — please check you copied the whole URL.")

    events = []
    for component in cal.walk("VEVENT"):
        dtstart, dtend = component.get("dtstart"), component.get("dtend")
        if not dtstart or not dtend:
            continue
        arrival, departure = _as_date(dtstart.dt), _as_date(dtend.dt)
        if departure <= arrival:
            continue
        uid = str(component.get("uid") or f"{arrival.isoformat()}-{departure.isoformat()}")
        summary = str(component.get("summary") or "").strip()
        events.append({"uid": uid, "arrival": arrival, "departure": departure, "summary": summary})
    return events


def sync_ical_feed(db: Session, property_id: int, channel_name: str, url: str) -> dict:
    """Fetch + parse the feed, then upsert Reservation rows. Idempotent — safe
    to call repeatedly (e.g. a manual "Sync now" click). Persists the outcome
    (success or failure) on the ICalFeed row either way, then raises
    ICalSyncError on failure so the caller can show it to the user."""
    channel = get_or_create_channel(db, channel_name)

    feed = db.query(ICalFeed).filter(ICalFeed.property_id == property_id, ICalFeed.channel_id == channel.id).first()
    if not feed:
        feed = ICalFeed(property_id=property_id, channel_id=channel.id, url=url)
        db.add(feed)
    feed.url = url

    try:
        content = _fetch(url)
        events = _parse(content)
    except ICalSyncError as e:
        feed.last_synced_at = datetime.utcnow()
        feed.last_sync_status = "error"
        feed.last_sync_message = str(e)
        db.commit()
        raise

    existing = {
        r.external_ref: r
        for r in db.query(Reservation).filter(
            Reservation.property_id == property_id,
            Reservation.channel_id == channel.id,
            Reservation.is_calendar_sync.is_(True),
        ).all()
    }

    seen_uids: set[str] = set()
    created = updated = unchanged = 0
    today = date.today()

    for ev in events:
        seen_uids.add(ev["uid"])
        nights = (ev["departure"] - ev["arrival"]).days
        existing_res = existing.get(ev["uid"])
        if existing_res:
            changed = (existing_res.arrival_date, existing_res.departure_date, existing_res.status) != (
                ev["arrival"], ev["departure"], ReservationStatus.CONFIRMED,
            )
            if changed:
                existing_res.arrival_date = ev["arrival"]
                existing_res.departure_date = ev["departure"]
                existing_res.nights = nights
                existing_res.status = ReservationStatus.CONFIRMED
                existing_res.cancellation_date = None
                existing_res.source_detail = ev["summary"]
                updated += 1
            else:
                unchanged += 1
        else:
            db.add(Reservation(
                property_id=property_id,
                channel_id=channel.id,
                external_ref=ev["uid"],
                booking_date=today,  # true booking date is not in the feed — see is_calendar_sync
                arrival_date=ev["arrival"],
                departure_date=ev["departure"],
                nights=nights,
                gross_revenue=None,
                net_revenue=None,
                status=ReservationStatus.CONFIRMED,
                is_calendar_sync=True,
                source_detail=ev["summary"],
            ))
            created += 1

    # A previously-synced reservation no longer in the feed was removed or
    # cancelled at the source — mark it cancelled rather than deleting it,
    # so history is preserved.
    cancelled = 0
    for uid, res in existing.items():
        if uid not in seen_uids and res.status != ReservationStatus.CANCELLED:
            res.status = ReservationStatus.CANCELLED
            res.cancellation_date = today
            cancelled += 1

    feed.last_synced_at = datetime.utcnow()
    feed.last_sync_status = "ok"
    feed.last_sync_message = f"{created} new, {updated} updated, {cancelled} cancelled, {unchanged} unchanged"
    db.commit()

    return {"created": created, "updated": updated, "cancelled": cancelled, "unchanged": unchanged, "total_events": len(events)}
