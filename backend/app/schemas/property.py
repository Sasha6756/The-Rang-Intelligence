from pydantic import BaseModel


class PropertyOut(BaseModel):
    id: int
    name: str
    address: str
    bedrooms: int
    currency: str
    default_display_currency: str | None = None
    timezone: str
    target_occupancy_pct: float
    target_adr: float
    is_demo: bool

    class Config:
        from_attributes = True


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    bedrooms: int | None = None
    currency: str | None = None
    default_display_currency: str | None = None
    timezone: str | None = None
    target_occupancy_pct: float | None = None
    target_adr: float | None = None
