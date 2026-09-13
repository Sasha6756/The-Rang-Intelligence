import json

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.schemas.importing import SOURCE_TO_CHANNEL
from app.services import import_service as svc
from app.services import revenue_service as rsvc

router = APIRouter(prefix="/api/revenue", tags=["revenue"])

CHANNEL_SOURCES = set(SOURCE_TO_CHANNEL.keys())  # booking_com / airbnb / direct


def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


async def _parse_upload(file: UploadFile) -> tuple[list[str], list[dict], str | None]:
    """Returns (headers, rows, pdf_warning). pdf_warning is set only for PDFs,
    to surface upfront that extraction is best-effort."""
    content = await file.read()
    if _is_pdf(file.filename):
        headers, rows = rsvc.extract_pdf_rows(content)
        return headers, rows, (
            "This was read from a PDF, which has no standard table format — double-check the sample rows "
            "and every proposed match below before confirming. An Excel/CSV export of the same report, if "
            "your platform offers one, will parse more reliably."
        )
    headers, rows = svc.parse_file(file.filename, content)
    return headers, rows, None


@router.post("/preview")
async def preview_revenue(
    source_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if source_type not in CHANNEL_SOURCES:
        raise HTTPException(400, f"Unknown source_type '{source_type}' — expected one of {list(CHANNEL_SOURCES)}")

    try:
        headers, rows, pdf_warning = await _parse_upload(file)
    except rsvc.RevenuePdfError as e:
        raise HTTPException(400, str(e))

    if not headers:
        raise HTTPException(400, "Could not read any columns from this file.")

    remembered = svc.get_remembered_mapping(db, current_user.property_id, "revenue")
    suggested = svc.suggest_mapping(headers, "revenue", remembered)
    clean, warnings = svc.validate_revenue_rows(rows, suggested)

    return {
        "headers": headers,
        "suggested_mapping": suggested,
        "system_fields": svc.REVENUE_FIELDS,
        "sample_rows": rows[:8],
        "row_count": len(rows),
        "valid_row_count": len(clean),
        "warnings": warnings[:50],
        "total_warning_count": len(warnings),
        "pdf_warning": pdf_warning,
    }


@router.post("/match")
async def match_revenue(
    source_type: str = Form(...),
    mapping: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if source_type not in CHANNEL_SOURCES:
        raise HTTPException(400, f"Unknown source_type '{source_type}'")

    try:
        _headers, rows, _pdf_warning = await _parse_upload(file)
    except rsvc.RevenuePdfError as e:
        raise HTTPException(400, str(e))

    mapping_dict = json.loads(mapping)
    clean, warnings = svc.validate_revenue_rows(rows, mapping_dict)
    if not clean:
        raise HTTPException(400, "No usable rows found — check the file and column mapping.")

    channel_name = SOURCE_TO_CHANNEL[source_type]
    matches = rsvc.match_revenue_rows(db, current_user.property_id, channel_name, clean)

    return {
        "matches": matches,
        "warnings": warnings[:50],
        "unmatched_count": sum(1 for m in matches if not m["candidates"]),
    }


@router.post("/commit")
async def commit_revenue(
    source_type: str = Form(...),
    mapping: str = Form(...),
    decisions: str = Form(...),  # JSON: [{row_index, action, reservation_id}]
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if source_type not in CHANNEL_SOURCES:
        raise HTTPException(400, f"Unknown source_type '{source_type}'")

    try:
        _headers, rows, _pdf_warning = await _parse_upload(file)
    except rsvc.RevenuePdfError as e:
        raise HTTPException(400, str(e))

    mapping_dict = json.loads(mapping)
    clean, _warnings = svc.validate_revenue_rows(rows, mapping_dict)
    decisions_list = json.loads(decisions)

    channel_name = SOURCE_TO_CHANNEL[source_type]
    result = rsvc.commit_revenue_decisions(db, current_user.property_id, channel_name, clean, decisions_list)
    if not _is_pdf(file.filename):
        svc.save_mapping(db, current_user.property_id, "revenue", mapping_dict)
    return result
