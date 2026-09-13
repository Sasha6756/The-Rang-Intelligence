"""
Flexible CSV/XLSX import: header detection, fuzzy auto-mapping, remembered
mappings, validation (dates, duplicates, missing values, currency, impossible
values) and a preview step before anything is written to the database.

Never silently corrupts or overwrites data: `commit_reservations` only runs
after the caller has confirmed a mapping (either auto-suggested or edited).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

import httpx
import openpyxl
from sqlalchemy.orm import Session

from app.models.core import Channel, Guest
from app.models.booking import Reservation, ReservationStatus
from app.models.review import Review
from app.models.competitor import Competitor, CompetitorRate
from app.models.importing import ImportBatch, ImportMapping

# ---- system field vocabularies per source type -----------------------------

RESERVATION_FIELDS = [
    "external_ref", "booking_date", "arrival_date", "departure_date",
    "guest_name", "guest_country", "adults", "children",
    "gross_revenue", "commission", "currency", "status", "cancellation_date",
    # Optional — most single-channel exports (a Booking.com/Airbnb download)
    # don't have these at all, but a hand-kept ledger covering every channel
    # often has its own "Source" column per row; when mapped, it overrides
    # the single channel picked in the UI on a per-row basis (see
    # validate_reservations / commit_reservations). "notes" maps straight
    # through to Reservation.source_detail.
    "channel", "notes",
]

REVIEW_FIELDS = ["review_date", "rating", "guest_country", "raw_text"]

COMPETITOR_RATE_FIELDS = ["competitor_name", "date", "nightly_rate", "available", "min_stay"]

# A payout/earnings report: dates identify *which* stay it paid out for (so it
# can be matched against an existing reservation), gross_revenue is the point
# of the whole exercise. departure_date is optional here — some payout
# exports only give arrival + nights — see validate_revenue_rows.
REVENUE_FIELDS = ["external_ref", "arrival_date", "departure_date", "nights", "guest_name", "gross_revenue", "commission", "currency"]

FIELDS_BY_SOURCE = {
    "booking_com": RESERVATION_FIELDS,
    "airbnb": RESERVATION_FIELDS,
    "direct": RESERVATION_FIELDS,
    "mixed": RESERVATION_FIELDS,
    "reviews": REVIEW_FIELDS,
    "competitor_rates": COMPETITOR_RATE_FIELDS,
    "revenue": REVENUE_FIELDS,
}

# common header synonyms -> system field, used for auto-suggestion
SYNONYMS: dict[str, list[str]] = {
    "booking_date": ["booking date", "reservation created", "reservation date", "date booked", "created"],
    "arrival_date": ["arrival", "arrival date", "check-in", "check in", "checkin date", "start date", "stay from"],
    "departure_date": ["departure", "departure date", "check-out", "check out", "checkout date", "end date", "stay to"],
    "guest_name": ["guest", "guest name", "customer", "customer name", "name", "guest / booking", "guest/booking"],
    "guest_country": ["country", "guest country", "nationality"],
    "adults": ["adults", "guests", "number of guests", "pax", "occupancy"],
    "children": ["children", "kids"],
    "gross_revenue": ["amount", "gross revenue", "total price", "total amount", "revenue", "price", "payout amount", "amount received", "total guest paid"],
    "commission": ["commission", "commission amount", "service fee", "ota commission"],
    "currency": ["currency", "currency received"],
    "status": ["status", "reservation status", "booking status"],
    "cancellation_date": ["cancellation date", "cancelled date", "date cancelled"],
    "external_ref": ["reservation id", "confirmation code", "booking id", "reservation number", "id"],
    "channel": ["source", "channel", "booking source", "platform"],
    "notes": ["notes", "note", "comment", "comments", "remarks"],
    "review_date": ["review date", "date", "submitted"],
    "rating": ["rating", "score", "overall rating"],
    "raw_text": ["review", "comment", "review text", "feedback", "text"],
    "competitor_name": ["competitor", "listing", "property", "name"],
    "date": ["date", "night", "stay date"],
    "nightly_rate": ["rate", "nightly rate", "price", "nightly price"],
    "available": ["available", "availability"],
    "min_stay": ["min stay", "minimum stay", "min nights"],
    "nights": ["nights", "length of stay", "los"],
}

# Payout/earnings-report header synonyms layered on top of SYNONYMS above —
# "amount" already maps to gross_revenue there, but payout reports use their
# own vocabulary for the money column specifically.
SYNONYMS["gross_revenue"] = SYNONYMS["gross_revenue"] + [
    "payout", "host payout", "payout amount", "gross earnings", "total payout", "earnings", "you earn",
]


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum() or ch.isspace()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


_SUBTOTAL_ROW_RE = re.compile(r"^subtotal$", re.IGNORECASE)
# Matches a hand-kept ledger's month-section header, e.g. "March 2026   (8 bookings)".
_SECTION_HEADER_ROW_RE = re.compile(r"^[a-z]+\s+\d{4}\s*\(\d+\s*bookings?\)$", re.IGNORECASE)


def _all_known_header_phrases(source_type: str | None) -> set[str]:
    """Normalized header text for every synonym of every system field —
    either just the fields relevant to `source_type`, or (when not given)
    every field across every source, for a source-agnostic best guess."""
    fields = FIELDS_BY_SOURCE.get(source_type) if source_type else None
    field_names = fields if fields else {f for flds in FIELDS_BY_SOURCE.values() for f in flds}
    phrases: set[str] = set()
    for f in field_names:
        phrases.add(_norm(f.replace("_", " ")))
        for syn in SYNONYMS.get(f, []):
            phrases.add(_norm(syn))
    return phrases


def _score_header_row(cells: list[str], phrases: set[str]) -> int:
    return sum(1 for c in cells if _norm(c) in phrases)


def _detect_header_row(grid: list[list[str]], source_type: str | None, scan_rows: int = 20) -> int:
    """Almost every real-world export puts the header on row 1 — but a
    hand-maintained business spreadsheet often has a title and instructions
    above the real header row (see the "Bookings Income" ledger format).
    Scans the first `scan_rows` rows and picks whichever looks most like a
    real header — by how many cells match a known system-field name or
    synonym — defaulting to row 0 unless a later row is a clearly better
    match, so ordinary files (header genuinely on row 1) are unaffected."""
    if not grid:
        return 0
    phrases = _all_known_header_phrases(source_type)
    best_idx, best_score = 0, _score_header_row(grid[0], phrases)
    for idx, row in enumerate(grid[1:scan_rows], start=1):
        score = _score_header_row(row, phrases)
        if score > best_score:
            best_idx, best_score = idx, score
    return best_idx


def _is_decorative_row(row: dict) -> bool:
    """True for a row that isn't data at all: fully blank, a "Subtotal"
    line, or a month-section header — all common in a hand-kept ledger
    that groups bookings under monthly headings with a running subtotal.
    Filtering these out here (rather than letting them fall through to
    validate_reservations as "missing date" warnings) keeps the warning
    list focused on rows that actually need attention.

    A Subtotal row usually has plenty of non-empty cells of its own — the
    month's totals, the "days left to book" note, the minimum-rate formula
    — so counting non-empty cells doesn't identify it. What's reliable is
    that its label ("Subtotal", or the month heading) always sits in the
    first column, the same column a real row would put its booking/arrival
    date in — which is itself never going to look like either pattern."""
    values = list(row.values())
    non_empty = [v.strip() for v in values if isinstance(v, str) and v.strip()]
    if not non_empty:
        return True
    first_cell = values[0].strip() if isinstance(values[0], str) else ""
    return bool(_SUBTOTAL_ROW_RE.match(first_cell) or _SECTION_HEADER_ROW_RE.match(first_cell))


def _rows_from_grid(grid: list[list[str]], source_type: str | None) -> tuple[list[str], list[dict]]:
    header_idx = _detect_header_row(grid, source_type)
    headers = [h.strip() for h in grid[header_idx]]
    rows = []
    for raw in grid[header_idx + 1:]:
        row = {headers[i]: (raw[i] if i < len(raw) else "") for i in range(len(headers))}
        if not _is_decorative_row(row):
            rows.append(row)
    return headers, rows


def parse_file(filename: str, content: bytes, source_type: str | None = None) -> tuple[list[str], list[dict]]:
    """Returns (headers, rows-as-dicts-of-strings). `source_type`, when
    given, narrows header detection to that source's own field vocabulary;
    omit it to match against every known field (still works, just slightly
    less targeted)."""
    if filename.lower().endswith((".xlsx", ".xlsm")):
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        grid = [
            ["" if v is None else str(v) for v in r]
            for r in ws.iter_rows(values_only=True)
            if not all(v is None for v in r)
        ]
        return _rows_from_grid(grid, source_type)
    else:
        text = content.decode("utf-8-sig", errors="replace")
        raw_rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
        return _rows_from_grid(raw_rows, source_type)


class GoogleSheetError(Exception):
    """Any user-facing failure fetching or reading a Google Sheet link."""


MAX_SHEET_BYTES = 10 * 1024 * 1024  # 10MB — generous for a spreadsheet export, guards against abuse


def _parse_google_sheet_url(url: str) -> tuple[str, str | None]:
    """Extracts (spreadsheet_id, gid) from any of the URL shapes Google hands
    out when you open a sheet or click Share/Copy link, e.g.:
      https://docs.google.com/spreadsheets/d/<id>/edit#gid=<gid>
      https://docs.google.com/spreadsheets/d/<id>/edit?usp=sharing
      https://docs.google.com/spreadsheets/d/<id>/
    `gid` identifies which tab; omitted, Google's export endpoint defaults to
    the first tab.
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise GoogleSheetError(
            "That doesn't look like a Google Sheets link — open the sheet in your browser and copy the full "
            "URL from the address bar."
        )
    sheet_id = match.group(1)
    gid_match = re.search(r"[#&?]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else None
    return sheet_id, gid


def fetch_google_sheet_csv(url: str) -> bytes:
    """Fetches one tab of a Google Sheet as CSV via the sheet's own export
    endpoint — read-only, nothing is ever written back to the sheet. This
    only works when the sheet is shared as "Anyone with the link" (Viewer is
    enough): Google serves this export URL without requiring a Google login
    for link-shared sheets, but a private sheet redirects to a login page
    (HTML) instead of CSV, which is treated as a sharing-settings error."""
    sheet_id, gid = _parse_google_sheet_url(url)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        export_url += f"&gid={gid}"

    try:
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            resp = client.get(export_url)
    except httpx.TimeoutException:
        raise GoogleSheetError("The Google Sheet link timed out. Please check the link and try again.")
    except httpx.HTTPError as e:
        raise GoogleSheetError(f"Could not reach that Google Sheet link ({e.__class__.__name__}).")

    content_type = resp.headers.get("content-type", "")
    if resp.status_code != 200 or "html" in content_type.lower():
        raise GoogleSheetError(
            "Couldn't read that sheet — it may not be shared publicly, or the link is wrong. In Google "
            'Sheets, click Share, change access to "Anyone with the link" (Viewer), then paste the link here again.'
        )
    if len(resp.content) > MAX_SHEET_BYTES:
        raise GoogleSheetError("That sheet is unexpectedly large — please double-check the link.")
    if not resp.content.strip():
        raise GoogleSheetError("That sheet (or tab) appears to be empty.")
    return resp.content


def suggest_mapping(headers: list[str], source_type: str, remembered: dict | None) -> dict[str, str | None]:
    fields = FIELDS_BY_SOURCE.get(source_type, RESERVATION_FIELDS)
    mapping: dict[str, str | None] = {}
    used_headers: set[str] = set()

    if remembered:
        for header, field in remembered.items():
            if header in headers and field in fields:
                mapping[field] = header
                used_headers.add(header)

    # Score every remaining (field, header) pair once, then assign in order
    # of confidence (highest score first) rather than by field declaration
    # order. Declaration order lets an earlier field grab a header with a
    # merely-adequate score before a later field that would have matched it
    # near-perfectly ever gets a turn — e.g. "external_ref" claiming a
    # "Booking date" column ahead of "booking_date" itself, a real
    # column-naming collision, not a hypothetical one.
    remaining_fields = [f for f in fields if f not in mapping]
    pair_scores: list[tuple[float, str, str]] = []
    for field in remaining_fields:
        candidates = SYNONYMS.get(field, [field])
        for header in headers:
            score = max(_similarity(header, c) for c in candidates + [field])
            if score >= 0.6:
                pair_scores.append((score, field, header))
    pair_scores.sort(key=lambda t: -t[0])

    assigned_fields: set[str] = set()
    for score, field, header in pair_scores:
        if field in assigned_fields or header in used_headers:
            continue
        mapping[field] = header
        used_headers.add(header)
        assigned_fields.add(field)

    for field in remaining_fields:
        if field not in mapping:
            mapping[field] = None

    return mapping


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "")).date()
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    if value is None:
        return None
    cleaned = str(value).replace(",", "").replace("$", "").replace("USD", "").replace("IDR", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def validate_reservations(rows: list[dict], mapping: dict[str, str | None]) -> tuple[list[dict], list[str]]:
    """Returns (clean_rows_ready_to_commit, human_readable_warnings)."""
    clean: list[dict] = []
    warnings: list[str] = []
    seen_refs: set[str] = set()

    for i, row in enumerate(rows, start=2):  # row 1 = header
        def get(field):
            header = mapping.get(field)
            return row.get(header, "") if header else ""

        booking_date = _parse_date(get("booking_date"))
        arrival_date = _parse_date(get("arrival_date"))
        departure_date = _parse_date(get("departure_date"))
        gross_revenue = _parse_float(get("gross_revenue"))
        guest_name = (get("guest_name") or "").strip()
        ext_ref_raw = (get("external_ref") or "").strip()
        if ext_ref_raw:
            ext_ref = ext_ref_raw
        else:
            # No reservation-ID column mapped — common for a hand-kept
            # ledger with no confirmation code at all. Derive a stable key
            # from the booking's own details rather than its row position,
            # so re-importing the same sheet later (after adding rows
            # above this one) doesn't shift everyone's identity and create
            # duplicates.
            basis = f"{arrival_date}|{departure_date}|{gross_revenue}|{guest_name}"
            ext_ref = "auto-" + hashlib.sha1(basis.encode()).hexdigest()[:12]

        if not arrival_date or not departure_date:
            warnings.append(f"Row {i}: missing/unparseable arrival or departure date — skipped.")
            continue
        if not booking_date:
            booking_date = arrival_date  # sensible fallback, flagged below
            warnings.append(f"Row {i}: missing booking date — defaulted to arrival date.")
        if departure_date <= arrival_date:
            warnings.append(f"Row {i}: departure on/before arrival — skipped (impossible date range).")
            continue
        nights = (departure_date - arrival_date).days
        if nights > 60:
            warnings.append(f"Row {i}: unusually long stay ({nights} nights) — kept, please verify.")
        if gross_revenue is None or gross_revenue < 0:
            warnings.append(f"Row {i}: missing/invalid revenue amount — skipped.")
            continue
        if gross_revenue == 0:
            warnings.append(f"Row {i}: zero revenue — kept but flagged, please verify.")
        if ext_ref in seen_refs:
            warnings.append(f"Row {i}: duplicate reference '{ext_ref}' within this file — kept, will be de-duplicated against existing records too.")
        seen_refs.add(ext_ref)

        commission = _parse_float(get("commission")) or 0.0
        status_raw = (get("status") or "confirmed").strip().lower()
        status = ReservationStatus.CANCELLED if "cancel" in status_raw else ReservationStatus.CONFIRMED

        clean.append(dict(
            external_ref=ext_ref,
            booking_date=booking_date,
            arrival_date=arrival_date,
            departure_date=departure_date,
            nights=nights,
            adults=int(_parse_float(get("adults")) or 2),
            children=int(_parse_float(get("children")) or 0),
            gross_revenue=gross_revenue,
            commission=commission,
            net_revenue=gross_revenue - commission,
            currency=(get("currency") or "USD").strip() or "USD",
            status=status,
            cancellation_date=_parse_date(get("cancellation_date")),
            guest_name=guest_name,
            guest_country=(get("guest_country") or "Unknown").strip() or "Unknown",
            channel_name=_normalize_channel_source(get("channel")) if (get("channel") or "").strip() else None,
            source_detail=(get("notes") or "").strip(),
        ))

    return clean, warnings


def validate_revenue_rows(rows: list[dict], mapping: dict[str, str | None]) -> tuple[list[dict], list[str]]:
    """A payout/earnings report only needs to identify *which stay* it paid
    for (so it can be matched to an existing reservation) and *how much* —
    everything else is optional. departure_date can be derived from
    arrival_date + nights if the report doesn't give it directly."""
    clean: list[dict] = []
    warnings: list[str] = []

    for i, row in enumerate(rows, start=2):
        def get(field):
            header = mapping.get(field)
            return row.get(header, "") if header else ""

        arrival_date = _parse_date(get("arrival_date"))
        departure_date = _parse_date(get("departure_date"))
        nights = _parse_float(get("nights"))
        gross_revenue = _parse_float(get("gross_revenue"))

        if not arrival_date:
            warnings.append(f"Row {i}: missing/unparseable arrival date — skipped.")
            continue
        if not departure_date and nights:
            departure_date = arrival_date + timedelta(days=int(nights))
        if not departure_date:
            warnings.append(f"Row {i}: no departure date and no nights count — skipped (can't identify the stay length).")
            continue
        if gross_revenue is None:
            warnings.append(f"Row {i}: missing/unparseable revenue amount — skipped.")
            continue

        clean.append(dict(
            external_ref=(get("external_ref") or "").strip(),
            arrival_date=arrival_date,
            departure_date=departure_date,
            guest_name=(get("guest_name") or "").strip(),
            gross_revenue=gross_revenue,
            commission=_parse_float(get("commission")) or 0.0,
            currency=(get("currency") or "USD").strip() or "USD",
        ))

    return clean, warnings


def validate_reviews(rows: list[dict], mapping: dict[str, str | None]) -> tuple[list[dict], list[str]]:
    clean, warnings = [], []
    for i, row in enumerate(rows, start=2):
        def get(field):
            header = mapping.get(field)
            return row.get(header, "") if header else ""

        review_date = _parse_date(get("review_date"))
        text = (get("raw_text") or "").strip()
        if not review_date:
            warnings.append(f"Row {i}: missing/unparseable review date — skipped.")
            continue
        if not text:
            warnings.append(f"Row {i}: empty review text — skipped.")
            continue
        rating = _parse_float(get("rating"))
        clean.append(dict(
            review_date=review_date,
            rating=rating,
            guest_country=(get("guest_country") or "Unknown").strip() or "Unknown",
            raw_text=text,
        ))
    return clean, warnings


def commit_reviews(db: Session, property_id: int, source_type: str, filename: str, clean_rows: list[dict], source_label: str) -> ImportBatch:
    from app.services.review_sentiment import analyze_review  # local import avoids circularity

    inserted = 0
    for row in clean_rows:
        sentiment_score, topics = analyze_review(row["raw_text"])
        review = Review(
            property_id=property_id, source=source_label, review_date=row["review_date"],
            rating=row["rating"], guest_country=row["guest_country"], raw_text=row["raw_text"],
            sentiment_score=sentiment_score,
        )
        db.add(review)
        db.flush()
        from app.models.review import ReviewTopic
        for topic, sentiment, snippet in topics:
            db.add(ReviewTopic(review_id=review.id, topic=topic, sentiment=sentiment, snippet=snippet))
        inserted += 1

    batch = ImportBatch(property_id=property_id, source_type=source_type, filename=filename, row_count=inserted, status="completed")
    db.add(batch)
    db.commit()
    return batch


def validate_competitor_rates(rows: list[dict], mapping: dict[str, str | None]) -> tuple[list[dict], list[str]]:
    clean, warnings = [], []
    for i, row in enumerate(rows, start=2):
        def get(field):
            header = mapping.get(field)
            return row.get(header, "") if header else ""

        name = (get("competitor_name") or "").strip()
        the_date = _parse_date(get("date"))
        rate = _parse_float(get("nightly_rate"))
        if not name or not the_date:
            warnings.append(f"Row {i}: missing competitor name or date — skipped.")
            continue
        available_raw = (get("available") or "true").strip().lower()
        clean.append(dict(
            competitor_name=name, date=the_date, nightly_rate=rate,
            available=available_raw not in ("false", "0", "no"),
            min_stay=int(_parse_float(get("min_stay")) or 1),
        ))
    return clean, warnings


def commit_competitor_rates(db: Session, property_id: int, filename: str, clean_rows: list[dict]) -> ImportBatch:
    inserted = 0
    for row in clean_rows:
        competitor = db.query(Competitor).filter(
            Competitor.property_id == property_id, Competitor.name == row["competitor_name"]
        ).first()
        if not competitor:
            competitor = Competitor(property_id=property_id, name=row["competitor_name"])
            db.add(competitor)
            db.flush()
        db.add(CompetitorRate(
            competitor_id=competitor.id, date=row["date"], nightly_rate=row["nightly_rate"],
            available=row["available"], min_stay=row["min_stay"], source="csv",
        ))
        inserted += 1
    batch = ImportBatch(property_id=property_id, source_type="competitor_rates", filename=filename, row_count=inserted, status="completed")
    db.add(batch)
    db.commit()
    return batch


def get_or_create_channel(db: Session, name: str) -> Channel:
    channel = db.query(Channel).filter(Channel.name == name).first()
    if not channel:
        channel = Channel(name=name, default_commission_pct=0.0, is_ota=name != "Direct")
        db.add(channel)
        db.flush()
    return channel


def _normalize_channel_source(raw: str) -> str:
    """Maps a free-text source value (as hand-typed in a booking ledger,
    not a fixed dropdown) to one of the app's canonical channels."""
    text = raw.strip().lower()
    if "airbnb" in text:
        return "Airbnb"
    if "booking" in text:  # "Booking.com", "Booking.com payout", ...
        return "Booking.com"
    if "direct" in text or "website" in text:
        return "Direct"
    return "Other"  # word of mouth, Instagram, unrecognized, etc.


def commit_reservations(
    db: Session, property_id: int, source_type: str, filename: str,
    clean_rows: list[dict], channel_name: str,
) -> ImportBatch:
    """`channel_name` is the default/fallback channel for the whole batch —
    a single-source file (a Booking.com or Airbnb export) uses it for every
    row. A row can override it individually via `channel_name` in its own
    clean-row dict (set by validate_reservations when a "channel"/"source"
    column was mapped), which is how a mixed-source ledger with its own
    per-row Source column gets each booking filed under the right channel
    instead of all of them landing under whatever was picked in the UI."""
    default_channel = get_or_create_channel(db, channel_name)
    channel_cache: dict[str, Channel] = {channel_name: default_channel}

    def resolve_channel(row_channel_name: str | None) -> Channel:
        name = row_channel_name or channel_name
        if name not in channel_cache:
            channel_cache[name] = get_or_create_channel(db, name)
        return channel_cache[name]

    existing_refs = {
        (r.channel_id, r.external_ref) for r in db.query(Reservation.channel_id, Reservation.external_ref)
        .filter(Reservation.property_id == property_id).all()
    }

    inserted = 0
    for row in clean_rows:
        channel = resolve_channel(row.get("channel_name"))
        if (channel.id, row["external_ref"]) in existing_refs:
            continue  # duplicate vs. existing database — skip silently-but-counted
        guest = None
        if row["guest_name"] or row["guest_country"] != "Unknown":
            guest = Guest(property_id=property_id, name=row["guest_name"], country=row["guest_country"])
            db.add(guest)
            db.flush()

        db.add(Reservation(
            property_id=property_id,
            channel_id=channel.id,
            guest_id=guest.id if guest else None,
            external_ref=row["external_ref"],
            booking_date=row["booking_date"],
            arrival_date=row["arrival_date"],
            departure_date=row["departure_date"],
            nights=row["nights"],
            adults=row["adults"],
            children=row["children"],
            gross_revenue=row["gross_revenue"],
            commission=row["commission"],
            net_revenue=row["net_revenue"],
            currency=row["currency"],
            status=row["status"],
            cancellation_date=row["cancellation_date"],
            source_detail=row.get("source_detail", ""),
        ))
        existing_refs.add((channel.id, row["external_ref"]))
        inserted += 1

    batch = ImportBatch(
        property_id=property_id, source_type=source_type, filename=filename,
        row_count=inserted, status="completed",
    )
    db.add(batch)
    db.commit()
    return batch


def save_mapping(db: Session, property_id: int, source_type: str, mapping: dict) -> None:
    existing = (
        db.query(ImportMapping)
        .filter(ImportMapping.property_id == property_id, ImportMapping.source_type == source_type)
        .first()
    )
    if existing:
        existing.column_map = mapping
        existing.updated_at = datetime.utcnow()
    else:
        db.add(ImportMapping(property_id=property_id, source_type=source_type, column_map=mapping))
    db.commit()


def get_remembered_mapping(db: Session, property_id: int, source_type: str) -> dict | None:
    m = (
        db.query(ImportMapping)
        .filter(ImportMapping.property_id == property_id, ImportMapping.source_type == source_type)
        .first()
    )
    return m.column_map if m else None
