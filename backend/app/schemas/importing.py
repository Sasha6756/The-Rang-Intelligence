from pydantic import BaseModel


class MappingPreviewResponse(BaseModel):
    headers: list[str]
    suggested_mapping: dict[str, str | None]
    system_fields: list[str]
    sample_rows: list[dict]
    row_count: int


class ImportCommitResponse(BaseModel):
    batch_id: int
    rows_imported: int
    warnings: list[str]


SOURCE_TO_CHANNEL = {
    "booking_com": "Booking.com",
    "airbnb": "Airbnb",
    "direct": "Direct",
    # A ledger covering every channel in one sheet, with its own per-row
    # "Source" column — "Other" here is only the fallback for a row whose
    # Source cell doesn't map to anything (see _normalize_channel_source).
    "mixed": "Other",
}

SOURCE_TO_REVIEW_LABEL = {
    "reviews_booking_com": "Booking.com",
    "reviews_airbnb": "Airbnb",
    "reviews_google": "Google",
    "reviews_direct": "Direct",
}
