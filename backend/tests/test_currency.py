"""
Tests for the multi-currency exchange-rate engine and conversion service.
Network calls to the live provider are never made in tests — fetches are
monkeypatched with deterministic canned rates so results are reproducible.
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.exchange_rate import ExchangeRate
from app.services import currency_service as csvc


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_rate(db, quote, rate, effective_date, source="test-fixture"):
    db.add(ExchangeRate(
        base_currency="IDR", quote_currency=quote, rate=rate, source=source,
        retrieved_at=datetime.utcnow(), effective_date=effective_date,
    ))
    db.commit()


# --- conversion accuracy -------------------------------------------------

def test_convert_same_currency_is_identity(db):
    assert csvc.convert(db, 1000.0, "USD", "USD") == 1000.0


def test_convert_none_amount_returns_none(db):
    assert csvc.convert(db, None, "USD", "AUD") is None


def test_convert_pivot_to_quote_and_back(db):
    # 1 IDR = 0.000065 USD  ->  1,000,000 IDR = 65 USD
    _seed_rate(db, "USD", 0.000065, date(2026, 9, 1))
    assert csvc.convert(db, 1_000_000, "IDR", "USD") == pytest.approx(65.0)
    # and the inverse: 65 USD -> 1,000,000 IDR
    assert csvc.convert(db, 65.0, "USD", "IDR") == pytest.approx(1_000_000, rel=1e-6)


def test_convert_triangulates_between_two_non_pivot_currencies(db):
    # 1 IDR = 0.0000975 AUD ; 1 IDR = 0.000065 USD
    # => 1 AUD = 0.000065 / 0.0000975 USD ≈ 0.6667 USD
    _seed_rate(db, "AUD", 0.0000975, date(2026, 9, 1))
    _seed_rate(db, "USD", 0.000065, date(2026, 9, 1))
    result = csvc.convert(db, 100.0, "AUD", "USD")
    assert result == pytest.approx(100.0 * (0.000065 / 0.0000975), rel=1e-9)


def test_convert_unsupported_currency_raises(db):
    _seed_rate(db, "USD", 0.000065, date(2026, 9, 1))
    with pytest.raises(csvc.CurrencyError):
        csvc.convert(db, 100.0, "USD", "GBP")


def test_convert_raises_when_no_rate_data_at_all(db):
    with pytest.raises(csvc.CurrencyError):
        csvc.convert(db, 100.0, "USD", "AUD")


def test_convert_safe_swallows_error(db):
    assert csvc.convert_safe(db, 100.0, "USD", "AUD") is None


# --- historical vs current rate mode -------------------------------------

def test_historical_mode_uses_rate_effective_on_given_date(db):
    _seed_rate(db, "USD", 0.000060, date(2026, 1, 1))
    _seed_rate(db, "USD", 0.000070, date(2026, 6, 1))

    # a date between the two rates should use the earlier (nearest-before) one
    result = csvc.convert(db, 1_000_000, "IDR", "USD", on_date=date(2026, 3, 15))
    assert result == pytest.approx(60.0)

    # current-rate mode (on_date=None) should use the latest rate regardless
    current = csvc.convert(db, 1_000_000, "IDR", "USD", on_date=None)
    assert current == pytest.approx(70.0)


def test_historical_mode_before_any_data_falls_back_to_earliest_and_flags_stale(db):
    _seed_rate(db, "USD", 0.000065, date(2026, 6, 1))
    info = csvc.get_rate_info(db, "USD", on_date=date(2020, 1, 1))
    assert info is not None
    assert info.rate == pytest.approx(0.000065)
    assert info.is_stale is True


# --- get_status / staleness ------------------------------------------------

def test_get_status_reports_no_data_initially(db):
    status = csvc.get_status(db)
    assert status["has_data"] is False
    assert all(v["rate"] is None for v in status["currencies"].values())


def test_get_status_flags_stale_when_latest_rate_is_not_from_today(db):
    _seed_rate(db, "USD", 0.000065, date.today() - timedelta(days=3))
    _seed_rate(db, "AUD", 0.0000975, date.today() - timedelta(days=3))
    _seed_rate(db, "EUR", 0.00006, date.today() - timedelta(days=3))
    status = csvc.get_status(db)
    assert status["has_data"] is True
    assert status["currencies"]["USD"]["is_stale"] is True


def test_get_status_not_stale_when_rate_is_from_today(db):
    today = date.today()
    for q, r in (("USD", 0.000065), ("AUD", 0.0000975), ("EUR", 0.00006)):
        _seed_rate(db, q, r, today)
    status = csvc.get_status(db)
    assert all(v["is_stale"] is False for v in status["currencies"].values())


# --- refresh_rates (mocked provider) --------------------------------------

def test_refresh_rates_stores_new_rows_on_success(db, monkeypatch):
    fake_result = {
        "effective_date": date(2026, 9, 12),
        "rates": {"AUD": 0.0000975, "USD": 0.000065, "EUR": 0.00006},
    }
    monkeypatch.setattr(csvc, "fetch_latest_from_provider", lambda quote_currencies=None: fake_result)

    result = csvc.refresh_rates(db)
    assert result["ok"] is True
    assert result["effective_date"] == date(2026, 9, 12)

    rows = db.query(ExchangeRate).all()
    assert len(rows) == 3
    assert {r.quote_currency for r in rows} == {"AUD", "USD", "EUR"}


def test_refresh_rates_updates_same_day_row_instead_of_duplicating(db, monkeypatch):
    fake_result = {"effective_date": date(2026, 9, 12), "rates": {"AUD": 0.0000975, "USD": 0.000065, "EUR": 0.00006}}
    monkeypatch.setattr(csvc, "fetch_latest_from_provider", lambda quote_currencies=None: fake_result)
    csvc.refresh_rates(db)

    updated_result = {"effective_date": date(2026, 9, 12), "rates": {"AUD": 0.0000980, "USD": 0.000066, "EUR": 0.000061}}
    monkeypatch.setattr(csvc, "fetch_latest_from_provider", lambda quote_currencies=None: updated_result)
    csvc.refresh_rates(db)

    rows = db.query(ExchangeRate).filter(ExchangeRate.quote_currency == "USD").all()
    assert len(rows) == 1  # same effective_date -> updated in place, not duplicated
    assert rows[0].rate == pytest.approx(0.000066)


def test_refresh_rates_failure_never_raises_and_reports_last_known_date(db, monkeypatch):
    _seed_rate(db, "USD", 0.000065, date(2026, 9, 1))

    def boom(quote_currencies=None):
        raise csvc.CurrencyError("provider unreachable")

    monkeypatch.setattr(csvc, "fetch_latest_from_provider", boom)
    result = csvc.refresh_rates(db)
    assert result["ok"] is False
    assert "provider unreachable" in result["error"]
    assert result["last_known_effective_date"] == date(2026, 9, 1)


# --- convert_money_in_place (the response-shaping helper) -----------------

def test_convert_money_in_place_converts_recognised_keys_only(db):
    _seed_rate(db, "USD", 0.000065, date.today())
    payload = {
        "gross_revenue": 1_000_000, "occupancy_pct": 42.0, "reservation_count": 3,
        "nested": {"adr": 500_000, "label": "some string"},
        "rows": [{"net_revenue": 200_000}, {"net_revenue": None}],
    }
    csvc.convert_money_in_place(db, payload, "IDR", "USD", "current")

    assert payload["gross_revenue"] == pytest.approx(65.0)
    assert payload["occupancy_pct"] == 42.0  # untouched — not a money key
    assert payload["reservation_count"] == 3  # untouched
    assert payload["nested"]["adr"] == pytest.approx(32.5)
    assert payload["nested"]["label"] == "some string"  # untouched
    assert payload["rows"][0]["net_revenue"] == pytest.approx(13.0)
    assert payload["rows"][1]["net_revenue"] is None  # None left alone, not converted to 0


def test_convert_money_in_place_is_noop_for_same_currency(db):
    payload = {"gross_revenue": 1000.0}
    csvc.convert_money_in_place(db, payload, "USD", "usd", "current")  # case-insensitive
    assert payload["gross_revenue"] == 1000.0


def test_convert_money_in_place_uses_historical_date_per_row(db):
    _seed_rate(db, "USD", 0.000060, date(2026, 1, 1))
    _seed_rate(db, "USD", 0.000070, date(2026, 6, 1))
    rows = [
        {"arrival_date": date(2026, 2, 1), "gross_revenue": 1_000_000},
        {"arrival_date": date(2026, 7, 1), "gross_revenue": 1_000_000},
    ]
    csvc.convert_money_in_place(db, rows, "IDR", "USD", "historical")
    assert rows[0]["gross_revenue"] == pytest.approx(60.0)
    assert rows[1]["gross_revenue"] == pytest.approx(70.0)


# --- formatting -------------------------------------------------------------

def test_format_money_idr_has_no_decimals():
    assert csvc.format_money(1_500_000, "IDR") == "Rp1,500,000"


def test_format_money_usd_has_two_decimals():
    assert csvc.format_money(1234.5, "USD") == "$1,234.50"


def test_format_money_none_is_em_dash():
    assert csvc.format_money(None, "USD") == "—"


# --- provider HTTP parsing ---------------------------------------------------
# frankfurter.dev's v2 /rates endpoint returns a flat array of
# {date, base, quote, rate} records (one per requested quote currency) rather
# than a single object with a nested "rates" map (that older shape belongs to
# v1 /latest). These tests pin fetch_latest_from_provider to the real v2 shape
# so a future accidental revert to the v1 request/response format is caught.

class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_fetch_latest_from_provider_parses_v2_array_response(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse([
            {"date": "2026-09-13", "base": "IDR", "quote": "AUD", "rate": 0.0000914},
            {"date": "2026-09-13", "base": "IDR", "quote": "USD", "rate": 0.0000649},
            {"date": "2026-09-13", "base": "IDR", "quote": "EUR", "rate": 0.0000555},
        ])

    monkeypatch.setattr(csvc.httpx, "get", fake_get)
    result = csvc.fetch_latest_from_provider(["AUD", "USD", "EUR"])

    assert captured["url"] == csvc.PROVIDER_URL == "https://api.frankfurter.dev/v2/rates"
    assert captured["params"] == {"base": "IDR", "quotes": "AUD,USD,EUR"}
    assert result["effective_date"] == date(2026, 9, 13)
    assert result["rates"] == {"AUD": 0.0000914, "USD": 0.0000649, "EUR": 0.0000555}


def test_fetch_latest_from_provider_raises_on_v1_style_object_response(monkeypatch):
    """Guards against silently accepting the old v1 {"rates": {...}} shape."""
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"base": "IDR", "date": "2026-09-13", "rates": {"AUD": 0.0000914}})

    monkeypatch.setattr(csvc.httpx, "get", fake_get)
    with pytest.raises(csvc.CurrencyError):
        csvc.fetch_latest_from_provider(["AUD"])


def test_fetch_latest_from_provider_raises_when_a_quote_is_missing(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse([{"date": "2026-09-13", "base": "IDR", "quote": "AUD", "rate": 0.0000914}])

    monkeypatch.setattr(csvc.httpx, "get", fake_get)
    with pytest.raises(csvc.CurrencyError):
        csvc.fetch_latest_from_provider(["AUD", "USD", "EUR"])
