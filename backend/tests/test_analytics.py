"""
Sanity tests for the deterministic analytics engine — the part of the system
that must never be wrong, since the recommendation engine and AI narrative
layer both build on it.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.core import Channel, Guest
from app.models.booking import Reservation, ReservationStatus
from app.services import analytics_service as svc


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _add_reservation(db, channel, arrival, departure, gross_revenue, status=ReservationStatus.CONFIRMED, booking_date=None):
    nights = (departure - arrival).days
    r = Reservation(
        property_id=1, channel_id=channel.id, external_ref=f"t-{arrival}-{departure}",
        booking_date=booking_date or date(arrival.year - 1, 1, 1),
        arrival_date=arrival, departure_date=departure, nights=nights,
        adults=2, children=0, gross_revenue=gross_revenue, commission=0.0,
        net_revenue=gross_revenue, currency="USD", status=status,
    )
    db.add(r)
    db.commit()
    return r


def test_core_metrics_basic_occupancy_and_adr(db):
    channel = Channel(name="Direct", default_commission_pct=0.0, is_ota=False)
    db.add(channel)
    db.commit()

    # 4 nights booked out of a 10-night window at $1000/night = $4000 gross
    _add_reservation(db, channel, date(2026, 1, 1), date(2026, 1, 5), gross_revenue=4000.0)

    metrics = svc.core_metrics(db, property_id=1, start=date(2026, 1, 1), end=date(2026, 1, 11))
    assert metrics["available_nights"] == 10
    assert metrics["booked_nights"] == 4
    assert metrics["occupancy_pct"] == 40.0
    assert metrics["adr"] == 1000.0
    assert metrics["revpar"] == 400.0  # 4000 / 10
    assert metrics["gross_revenue"] == 4000.0


def test_core_metrics_ignores_cancelled_reservations(db):
    channel = Channel(name="Airbnb", default_commission_pct=3.0, is_ota=True)
    db.add(channel)
    db.commit()

    _add_reservation(db, channel, date(2026, 2, 1), date(2026, 2, 4), gross_revenue=3000.0, status=ReservationStatus.CANCELLED)

    metrics = svc.core_metrics(db, property_id=1, start=date(2026, 2, 1), end=date(2026, 2, 11))
    assert metrics["booked_nights"] == 0
    assert metrics["gross_revenue"] == 0.0


def test_core_metrics_partial_overlap_is_prorated(db):
    channel = Channel(name="Direct", default_commission_pct=0.0, is_ota=False)
    db.add(channel)
    db.commit()

    # 10-night stay spanning the window boundary: only 2 of its nights fall inside [Mar 1, Mar 3)
    _add_reservation(db, channel, date(2026, 2, 27), date(2026, 3, 9), gross_revenue=10000.0)

    metrics = svc.core_metrics(db, property_id=1, start=date(2026, 3, 1), end=date(2026, 3, 3))
    assert metrics["available_nights"] == 2
    assert metrics["booked_nights"] == 2
    assert metrics["gross_revenue"] == pytest.approx(2000.0)  # 2/10 of the total


def test_cancellation_rate(db):
    channel = Channel(name="Booking.com", default_commission_pct=15.0, is_ota=True)
    db.add(channel)
    db.commit()

    for i in range(8):
        status = ReservationStatus.CANCELLED if i < 2 else ReservationStatus.CONFIRMED
        _add_reservation(
            db, channel, date(2026, 4, 1 + i), date(2026, 4, 3 + i), gross_revenue=1000.0,
            status=status, booking_date=date(2026, 3, 1),
        )

    result = svc.cancellation_rate(db, property_id=1, start=date(2026, 3, 1), end=date(2026, 3, 2))
    assert result["total"] == 8
    assert result["cancelled"] == 2
    assert result["rate_pct"] == 25.0


def test_find_availability_gaps_detects_empty_stretch(db):
    channel = Channel(name="Direct", default_commission_pct=0.0, is_ota=False)
    db.add(channel)
    db.commit()

    # nothing booked at all in the horizon -> the whole horizon is one gap
    gaps = svc.find_availability_gaps(db, property_id=1, horizon_days=10, min_gap_nights=2)
    assert len(gaps) == 1
    assert gaps[0]["nights"] == 10
