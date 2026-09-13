"""
Reconcile a separately-uploaded revenue/payout report (CSV, XLSX, or PDF)
against existing reservations — most importantly the calendar-synced ones
from ical_service, which have real dates but no price.

This never auto-writes a price to a reservation. It proposes candidate
matches (by exact reference, then by date closeness) and returns them for a
human to confirm, reassign, or reject in the UI — matching is doing exactly
what the brief calls for: "manual reconciliation to confirm the app is
matching bookings correctly."
"""
from __future__ import annotations

import io
from datetime import date, timedelta

import pdfplumber
from sqlalchemy.orm import Session

from app.models.booking import Reservation, ReservationStatus
from app.services.import_service import get_or_create_channel


class RevenuePdfError(Exception):
    pass


def extract_pdf_rows(content: bytes) -> tuple[list[str], list[dict]]:
    """Best-effort table extraction from a payout/invoice PDF, shaped like
    parse_file()'s (headers, rows-as-dicts) so it can reuse the same mapping
    and validation code as CSV/XLSX. PDF layouts vary enormously — this is
    inherently less reliable, which is exactly why every row still goes
    through the same manual match-confirmation step before anything is saved.
    """
    # pdfplumber's default table-finding strategy ("lines") only works when a
    # PDF actually draws ruling lines/borders around cells. Many real payout
    # statements (and anything built without an explicit grid style) have no
    # visible borders at all, so we also try a "text" strategy — which infers
    # rows/columns purely from the whitespace alignment of the text itself —
    # and keep whichever strategy finds more data.
    TABLE_STRATEGIES = [
        {},  # pdfplumber defaults (lines-based)
        {"vertical_strategy": "text", "horizontal_strategy": "text"},
    ]

    def _extract_with_settings(table_settings: dict) -> tuple[list[str] | None, list[dict]]:
        rows: list[dict] = []
        headers: list[str] | None = None
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings) if table_settings else page.extract_tables()
                for table in tables or []:
                    if not table or len(table) < 2:
                        continue
                    first_row = [str(c or "").strip() for c in table[0]]
                    looks_like_header = first_row and sum(
                        1 for c in first_row if c and not any(ch.isdigit() for ch in c)
                    ) >= max(len(first_row) / 2, 1)

                    if headers is None and looks_like_header:
                        headers = first_row
                        body = table[1:]
                    else:
                        body = table[1:] if looks_like_header else table

                    for r in body:
                        cells = [str(c or "").strip() for c in r]
                        if not any(cells):
                            continue
                        if headers and len(cells) == len(headers):
                            rows.append(dict(zip(headers, cells)))
                        elif not headers:
                            rows.append({f"column_{i + 1}": v for i, v in enumerate(cells)})
        return headers, rows

    try:
        headers: list[str] | None = None
        rows: list[dict] = []
        for table_settings in TABLE_STRATEGIES:
            try:
                candidate_headers, candidate_rows = _extract_with_settings(table_settings)
            except Exception:
                continue
            if len(candidate_rows) > len(rows):
                headers, rows = candidate_headers, candidate_rows
    except Exception as e:
        raise RevenuePdfError(f"Could not read that PDF ({e.__class__.__name__}). Try exporting as CSV/Excel instead if possible.")

    if headers is None and rows:
        headers = sorted({k for r in rows for k in r})
    if not rows:
        raise RevenuePdfError(
            "Couldn't find a table in that PDF. Some payout PDFs are formatted as text rather than a "
            "table and can't be reliably extracted — an Excel/CSV export of the same report, if available, "
            "will work much better."
        )
    return headers or [], rows


def find_candidates(
    db: Session, property_id: int, channel_id: int, arrival_date: date, departure_date: date,
    external_ref: str, limit: int = 5,
) -> list[dict]:
    """Ranked candidate reservations for one revenue row: exact reference
    match first, then exact date match, then near-date matches within a
    growing window. Never returns a single "correct" answer — the caller
    always presents these as choices, defaulting to the top one."""
    base = db.query(Reservation).filter(
        Reservation.property_id == property_id,
        Reservation.channel_id == channel_id,
        Reservation.status != ReservationStatus.CANCELLED,
    )

    scored: dict[int, tuple[int, str, Reservation]] = {}

    if external_ref:
        for r in base.filter(Reservation.external_ref == external_ref).all():
            scored[r.id] = (0, "exact reference match", r)

    for tolerance, label in ((0, "exact dates"), (1, "dates within 1 day"), (3, "dates within 3 days")):
        window_start, window_end = arrival_date - timedelta(days=tolerance), arrival_date + timedelta(days=tolerance)
        for r in base.filter(Reservation.arrival_date >= window_start, Reservation.arrival_date <= window_end).all():
            if r.id in scored:
                continue
            date_gap = abs((r.arrival_date - arrival_date).days) + abs((r.departure_date - departure_date).days)
            rank = 1 + tolerance  # exact-date matches (tolerance 0) outrank near matches
            scored[r.id] = (rank, label if date_gap else "exact dates", r)

    ranked = sorted(scored.values(), key=lambda t: t[0])[:limit]
    return [
        {
            "reservation_id": r.id,
            "reason": reason,
            "arrival_date": r.arrival_date,
            "departure_date": r.departure_date,
            "nights": r.nights,
            "external_ref": r.external_ref,
            "already_priced": r.gross_revenue is not None,
            "current_gross_revenue": r.gross_revenue,
            "is_calendar_sync": r.is_calendar_sync,
        }
        for _, reason, r in ranked
    ]


def match_revenue_rows(db: Session, property_id: int, channel_name: str, clean_rows: list[dict]) -> list[dict]:
    channel = get_or_create_channel(db, channel_name)
    results = []
    for i, row in enumerate(clean_rows):
        candidates = find_candidates(
            db, property_id, channel.id, row["arrival_date"], row["departure_date"], row["external_ref"],
        )
        results.append({
            "row_index": i,
            "parsed": row,
            "candidates": candidates,
            "suggested_reservation_id": candidates[0]["reservation_id"] if candidates else None,
        })
    return results


def commit_revenue_decisions(
    db: Session, property_id: int, channel_name: str, clean_rows: list[dict], decisions: list[dict],
) -> dict:
    """`decisions`: [{row_index, action: "match"|"create_new"|"skip", reservation_id}].
    Only rows the user explicitly confirmed get written — anything not in
    `decisions`, or explicitly "skip", is left untouched."""
    channel = get_or_create_channel(db, channel_name)
    by_index = {d["row_index"]: d for d in decisions}

    matched = created = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(clean_rows):
        decision = by_index.get(i)
        if not decision or decision.get("action") == "skip":
            skipped += 1
            continue

        if decision["action"] == "match":
            res = db.get(Reservation, decision.get("reservation_id"))
            if not res or res.property_id != property_id:
                errors.append(f"Row {i + 1}: selected reservation not found — skipped.")
                continue
            res.gross_revenue = row["gross_revenue"]
            res.commission = row["commission"]
            res.net_revenue = row["gross_revenue"] - row["commission"]
            if row["currency"]:
                res.currency = row["currency"]
            matched += 1

        elif decision["action"] == "create_new":
            nights = (row["departure_date"] - row["arrival_date"]).days
            db.add(Reservation(
                property_id=property_id,
                channel_id=channel.id,
                external_ref=row["external_ref"] or f"revenue-row-{i}",
                booking_date=row["arrival_date"],  # not present in a payout report — best available fallback
                arrival_date=row["arrival_date"],
                departure_date=row["departure_date"],
                nights=nights,
                gross_revenue=row["gross_revenue"],
                commission=row["commission"],
                net_revenue=row["gross_revenue"] - row["commission"],
                currency=row["currency"] or "USD",
                status=ReservationStatus.CONFIRMED,
                # booking_date above is a fallback (arrival date), not the
                # real date the guest booked — a payout report doesn't carry
                # that. Reuse the same "don't trust booking_date/lead_time"
                # flag as calendar-synced rows so lead-time/booking-pace/
                # cancellation-rate correctly exclude it, even though this
                # row (unlike a calendar sync) does have a real price.
                is_calendar_sync=True,
                source_detail="Created from revenue reconciliation (no matching booking found)",
            ))
            created += 1

    db.commit()
    return {"matched": matched, "created": created, "skipped": skipped, "errors": errors}
