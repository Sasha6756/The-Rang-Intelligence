from datetime import date
from pydantic import BaseModel


class ReservationOut(BaseModel):
    id: int
    channel_name: str
    guest_country: str | None = None
    external_ref: str
    booking_date: date
    arrival_date: date
    departure_date: date
    nights: int
    adults: int
    children: int
    gross_revenue: float
    commission: float
    net_revenue: float
    adr: float
    lead_time_days: int
    currency: str
    status: str

    class Config:
        from_attributes = True


class CalendarDayOut(BaseModel):
    date: date
    is_booked: bool
    adr: float | None = None
    guest_country: str | None = None
    nights_remaining_in_stay: int | None = None
