"""
Flexible CSV/XLSX import: header detection, fuzzy auto-mapping, remembered
mappings, validation (dates, duplicates, missing values, currency, impossible
values) and a preview step before anything is written to the database.

Never silently corrupts or overwrites data: `commit_reservations` only runs
after the caller has confirmed a mapping (either auto-suggested or edited).
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

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
    "reviews": REVIEW_FIELDS,
    "competitor_rates": COMPETITOR_RATE_FIELDS,
    "revenue": REVENUE_FIELDS,
}

# common header synonyms -> system field, used for auto-suggestion
SYNONYMS: dict[str, list[str]] = {
    "booking_date": ["booking date", "reservation created", "reservation date", "date booked", "created"],
    "arrival_date": ["arrival", "arrival date", "check-in", "check in", "checkin date", "start date"],
    "departure_date": ["departure", "departure date", "check-out", "check out", "checkout date", "end date"],
    "guest_name": ["guest", "guest name", "customer", "customer name", "name"],
    "guest_country": ["country", "guest country", "nationality"],
    "adults": ["adults", "guests", "number of guests", "pax", "occupancy"],
    "children": ["children", "kids"],
    "gross_revenue": ["amount", "gross revenue", "total price", "total amount", "revenue", "price", "payout amount"],
    "commission": ["commission", "commission amount", "service fee", "ota commission"],
    "currency": ["currency"],
    "status": ["status", "reservation status", "booking status"],
    "cancellation_date": ["cancellation date", "cancelled date", "date cancelled"],
    "external_ref": ["reservation id", "confirmation code", "booking id", "reservation number", "id"],
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


def parse_file(filename: str, content: bytes) -> tuple[list[str], list[dict]]:
    """Returns (headers, rows-as-dicts-of-strings)."""
    if filename.lower().endswith((".xlsx", ".xlsm")):
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
        rows = []
        for r in rows_iter:
            if all(v is None for v in r):
                continue
            rows.append({headers[i]: ("" if r[i] is None else str(r[i])) for i in range(len(headers))})
        return headers, rows
    else:
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        rows = [dict(r) for r in reader]
        return headers, rows


def suggest_mapping(headers: list[str], source_type: str, remembered: dict | None) -> dict[str, str | None]:
    fields = FIELDS_BY_SOURCE.get(source_type, RESERVATION_FIELDS)
    mapping: dict[str, str | None] = {}
    used_headers: set[str] = set()

    if remembered:
        for header, field in remembered.items():
            if header in headers and field in fields:
                mapping[field] = header
                used_headers.add(header)

    for field in fields:
        if field in mapping:
            continue
        candidates = SYNONYMS.get(field, [field])
        best_header, best_score = None, 0.0
        for header in headers:
            if header in used_headers:
                continue
            score = max(_similarity(header, c) for c in candidates + [field])
            if score > best_score:
                best_header, best_score = header, score
        mapping[field] = best_header if best_score >= 0.6 else None
        if mapping[field]:
            used_headers.add(mapping[field])

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
        ext_ref = (get("external_ref") or "").strip() or f"row-{i}"

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
            guest_name=(get("guest_name") or "").strip(),
            guest_country=(get("guest_country") or "Unknown").strip() or "Unknown",
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


def commit_reservations(
    db: Session, property_id: int, source_type: str, filename: str,
    clean_rows: list[dict], channel_name: str,
) -> ImportBatch:
    channel = get_or_create_channel(db, channel_name)

    existing_refs = {
        r.external_ref for r in db.query(Reservation.external_ref)
        .filter(Reservation.property_id == property_id, Reservation.channel_id == channel.id).all()
    }

    inserted = 0
    for row in clean_rows:
        if row["external_ref"] in existing_refs:
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
        ))
        existing_refs.add(row["external_ref"])
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
