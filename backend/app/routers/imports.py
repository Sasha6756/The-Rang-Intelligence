import json

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.models.importing import ImportBatch
from app.models.ical_feed import ICalFeed
from app.schemas.importing import ImportCommitResponse, SOURCE_TO_CHANNEL, SOURCE_TO_REVIEW_LABEL
from app.services import import_service as svc
from app.services import ical_service

router = APIRouter(prefix="/api/imports", tags=["imports"])

RESERVATION_SOURCES = {"booking_com", "airbnb", "direct"}
REVIEW_SOURCES = set(SOURCE_TO_REVIEW_LABEL.keys())

ICAL_CHANNELS = {"airbnb": "Airbnb", "booking_com": "Booking.com"}


@router.post("/preview")
async def preview_import(
    source_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    headers, rows = svc.parse_file(file.filename, content)
    if not headers:
        raise HTTPException(400, "Could not read any columns from this file.")

    mapping_source_key = "reviews" if source_type in REVIEW_SOURCES else source_type
    remembered = svc.get_remembered_mapping(db, current_user.property_id, mapping_source_key)
    lookup_key = "reviews" if source_type in REVIEW_SOURCES else ("competitor_rates" if source_type == "competitor_rates" else source_type)
    suggested = svc.suggest_mapping(headers, lookup_key, remembered)

    system_fields = svc.FIELDS_BY_SOURCE.get(lookup_key, svc.RESERVATION_FIELDS)

    # run validation with the *suggested* mapping so the preview shows real warnings
    if source_type in RESERVATION_SOURCES:
        clean, warnings = svc.validate_reservations(rows, suggested)
    elif source_type in REVIEW_SOURCES:
        clean, warnings = svc.validate_reviews(rows, suggested)
    elif source_type == "competitor_rates":
        clean, warnings = svc.validate_competitor_rates(rows, suggested)
    else:
        raise HTTPException(400, f"Unknown source_type '{source_type}'")

    return {
        "headers": headers,
        "suggested_mapping": suggested,
        "system_fields": system_fields,
        "sample_rows": rows[:8],
        "row_count": len(rows),
        "valid_row_count": len(clean),
        "warnings": warnings[:50],
        "total_warning_count": len(warnings),
    }


@router.post("/commit", response_model=ImportCommitResponse)
async def commit_import(
    source_type: str = Form(...),
    mapping: str = Form(...),  # JSON-encoded {field: header}
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    headers, rows = svc.parse_file(file.filename, content)
    mapping_dict = json.loads(mapping)

    if source_type in RESERVATION_SOURCES:
        clean, warnings = svc.validate_reservations(rows, mapping_dict)
        channel_name = SOURCE_TO_CHANNEL[source_type]
        batch = svc.commit_reservations(db, current_user.property_id, source_type, file.filename, clean, channel_name)
        svc.save_mapping(db, current_user.property_id, source_type, mapping_dict)
    elif source_type in REVIEW_SOURCES:
        clean, warnings = svc.validate_reviews(rows, mapping_dict)
        label = SOURCE_TO_REVIEW_LABEL[source_type]
        batch = svc.commit_reviews(db, current_user.property_id, source_type, file.filename, clean, label)
        svc.save_mapping(db, current_user.property_id, "reviews", mapping_dict)
    elif source_type == "competitor_rates":
        clean, warnings = svc.validate_competitor_rates(rows, mapping_dict)
        batch = svc.commit_competitor_rates(db, current_user.property_id, file.filename, clean)
        svc.save_mapping(db, current_user.property_id, "competitor_rates", mapping_dict)
    else:
        raise HTTPException(400, f"Unknown source_type '{source_type}'")

    return ImportCommitResponse(batch_id=batch.id, rows_imported=batch.row_count, warnings=warnings[:50])


class ICalSyncRequest(BaseModel):
    channel: str  # "airbnb" | "booking_com"
    url: str


@router.post("/ical/sync")
def sync_ical(payload: ICalSyncRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    channel_name = ICAL_CHANNELS.get(payload.channel)
    if not channel_name:
        raise HTTPException(400, f"Unknown channel '{payload.channel}' — expected one of {list(ICAL_CHANNELS)}")
    url = payload.url.strip()
    if not url:
        raise HTTPException(400, "Please paste a calendar link first.")
    try:
        return ical_service.sync_ical_feed(db, current_user.property_id, channel_name, url)
    except ical_service.ICalSyncError as e:
        raise HTTPException(400, str(e))


@router.get("/ical/status")
def ical_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    feeds = db.query(ICalFeed).filter(ICalFeed.property_id == current_user.property_id).all()
    return [
        {
            "channel": f.channel.name if f.channel else None,
            "url": f.url,
            "last_synced_at": f.last_synced_at,
            "last_sync_status": f.last_sync_status,
            "last_sync_message": f.last_sync_message,
        }
        for f in feeds
    ]


@router.get("/history")
def import_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    batches = (
        db.query(ImportBatch)
        .filter(ImportBatch.property_id == current_user.property_id)
        .order_by(ImportBatch.uploaded_at.desc())
        .all()
    )
    return [
        {"id": b.id, "source_type": b.source_type, "filename": b.filename, "uploaded_at": b.uploaded_at,
         "row_count": b.row_count, "status": b.status}
        for b in batches
    ]
