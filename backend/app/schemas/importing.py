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
}

SOURCE_TO_REVIEW_LABEL = {
    "reviews_booking_com": "Booking.com",
    "reviews_airbnb": "Airbnb",
    "reviews_google": "Google",
    "reviews_direct": "Direct",
}
