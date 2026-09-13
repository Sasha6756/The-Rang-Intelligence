"""
Central multi-currency exchange-rate engine and conversion service.

Design (see docs/ARCHITECTURE.md section 11.3 for the full write-up):

- IDR is used as the internal pivot currency for RATE STORAGE — The Rang
  operates in Indonesia, so IDR is the most natural anchor for local pricing
  inputs — independent of whatever currency a given property's own figures
  happen to be recorded in (Property.currency).
- Rates are fetched once a day from a free, no-API-key provider
  (frankfurter.dev, tracking ECB + partner central bank reference rates) as
  IDR -> {AUD, USD, EUR}. Every conversion between any two of the four
  supported currencies is computed by triangulating through IDR, so only 3
  rates need to be stored/fetched per day to cover all 6 required pairs in
  both directions (IDR<->AUD, IDR<->USD, IDR<->EUR, AUD<->USD, AUD<->EUR,
  USD<->EUR).
- A fetch never overwrites a previous day's row — each day's rate is its own
  historical record — so both a "current-rate view" (today's latest rate)
  and a "historical-rate view" (the rate effective on a specific past date)
  are supported from the same table.
- If a fetch fails, the previous successful rate is reused for conversions
  and callers are told the data is stale via `is_stale` — this module never
  silently pretends a rate is fresher than it actually is, and never
  fabricates a rate that was never fetched.
- This is the ONLY place currency conversion math happens. Routers call
  `convert()` / `convert_money_in_place()` rather than duplicating
  conversion logic per endpoint (brief section 19).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate

SUPPORTED_CURRENCIES = ["IDR", "AUD", "USD", "EUR"]
PIVOT_CURRENCY = "IDR"
QUOTE_CURRENCIES = [c for c in SUPPORTED_CURRENCIES if c != PIVOT_CURRENCY]  # AUD, USD, EUR

PROVIDER_NAME = "frankfurter.dev (ECB + partner central bank reference rates)"
PROVIDER_URL = "https://api.frankfurter.dev/v2/rates"

CURRENCY_SYMBOLS = {"IDR": "Rp", "AUD": "A$", "USD": "$", "EUR": "€"}
CURRENCY_DECIMALS = {"IDR": 0, "AUD": 2, "USD": 2, "EUR": 2}


class CurrencyError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class RateInfo:
    quote_currency: str
    rate: float  # quote-currency units per 1 IDR
    effective_date: date
    retrieved_at: datetime
    source: str
    is_stale: bool  # the requested date isn't actually covered by this rate


def fetch_latest_from_provider(quote_currencies: list[str] | None = None) -> dict:
    """Hits the live provider once. Raises CurrencyError on any failure —
    callers decide whether to fall back to the last stored rate. Never
    retries silently and never invents a number: a failure here always
    surfaces as a failure to the caller."""
    quotes = quote_currencies or QUOTE_CURRENCIES
    try:
        resp = httpx.get(
            PROVIDER_URL,
            params={"base": PIVOT_CURRENCY, "quotes": ",".join(quotes)},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        # The v2 /rates endpoint returns a flat array of {date, base, quote, rate}
        # records (one per requested quote currency) rather than a single object
        # with a nested "rates" map (that shape belongs to the older v1 API).
        if not isinstance(data, list):
            raise CurrencyError(f"Unexpected provider response shape: expected a list, got {type(data).__name__}")
        rates: dict[str, float] = {}
        effective: date | None = None
        for row in data:
            q = row.get("quote")
            if q in quotes:
                rates[q] = float(row["rate"])
                effective = date.fromisoformat(row["date"])
        missing = [q for q in quotes if q not in rates]
        if missing:
            raise CurrencyError(f"Provider response missing rates for {missing}")
        return {"effective_date": effective, "rates": {q: rates[q] for q in quotes}}
    except CurrencyError:
        raise
    except Exception as e:
        raise CurrencyError(f"Could not reach exchange-rate provider ({e.__class__.__name__}): {e}")


def refresh_rates(db: Session) -> dict:
    """Fetch today's rates and store them, one row per quote currency. A
    re-fetch for a `effective_date` we already have updates that row in
    place (e.g. a manual refresh later the same day); a new date always
    inserts a new historical row rather than overwriting the old one.
    Never raises — on failure, returns {"ok": False, ...} so the scheduler
    and the manual-refresh endpoint can both surface the failure instead of
    crashing."""
    try:
        result = fetch_latest_from_provider()
    except CurrencyError as e:
        return {"ok": False, "error": str(e), "last_known_effective_date": _most_recent_effective_date(db)}

    now = _utcnow()
    for quote, rate in result["rates"].items():
        existing = (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.base_currency == PIVOT_CURRENCY,
                ExchangeRate.quote_currency == quote,
                ExchangeRate.effective_date == result["effective_date"],
            )
            .first()
        )
        if existing:
            existing.rate = rate
            existing.source = PROVIDER_NAME
            existing.retrieved_at = now
            existing.updated_at = now
        else:
            db.add(ExchangeRate(
                base_currency=PIVOT_CURRENCY, quote_currency=quote, rate=rate,
                source=PROVIDER_NAME, retrieved_at=now, effective_date=result["effective_date"],
                created_at=now, updated_at=now,
            ))
    db.commit()
    return {"ok": True, "effective_date": result["effective_date"], "rates": result["rates"], "source": PROVIDER_NAME}


def _most_recent_effective_date(db: Session) -> date | None:
    row = (
        db.query(ExchangeRate)
        .filter(ExchangeRate.base_currency == PIVOT_CURRENCY)
        .order_by(ExchangeRate.effective_date.desc())
        .first()
    )
    return row.effective_date if row else None


def _latest_row(db: Session, quote_currency: str, on_date: date | None) -> ExchangeRate | None:
    q = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == PIVOT_CURRENCY, ExchangeRate.quote_currency == quote_currency,
    )
    if on_date is not None:
        on_or_before = q.filter(ExchangeRate.effective_date <= on_date).order_by(ExchangeRate.effective_date.desc()).first()
        if on_or_before:
            return on_or_before
        # No rate exists that far back (e.g. a booking predates our first
        # fetch) — fall through to the earliest rate we do have rather than
        # returning nothing; get_rate_info marks this `is_stale`.
        return q.order_by(ExchangeRate.effective_date.asc()).first()
    return q.order_by(ExchangeRate.effective_date.desc()).first()


def get_rate_info(db: Session, quote_currency: str, on_date: date | None = None) -> RateInfo | None:
    if quote_currency == PIVOT_CURRENCY:
        return RateInfo(PIVOT_CURRENCY, 1.0, on_date or date.today(), _utcnow(), "identity", False)
    row = _latest_row(db, quote_currency, on_date)
    if row is None:
        return None
    is_stale = (on_date or date.today()) != row.effective_date
    return RateInfo(quote_currency, row.rate, row.effective_date, row.retrieved_at, row.source, is_stale)


def get_status(db: Session) -> dict:
    """Per-currency latest rate + staleness — backs the Settings 'Currency
    rates' panel and the top-bar rate badge."""
    today = date.today()
    currencies: dict[str, dict] = {}
    for q in QUOTE_CURRENCIES:
        info = get_rate_info(db, q)
        if info is None:
            currencies[q] = {"rate": None, "effective_date": None, "retrieved_at": None, "source": None, "is_stale": True}
        else:
            currencies[q] = {
                "rate": info.rate, "effective_date": info.effective_date,
                "retrieved_at": info.retrieved_at, "source": info.source, "is_stale": info.is_stale,
            }
    return {
        "base_currency": PIVOT_CURRENCY,
        "today": today,
        "currencies": currencies,
        "has_data": any(v["rate"] is not None for v in currencies.values()),
        "provider": PROVIDER_NAME,
    }


def convert(db: Session, amount: float | None, from_currency: str, to_currency: str, on_date: date | None = None) -> float | None:
    """Converts `amount` from_currency -> to_currency, triangulating through
    IDR. `on_date=None` uses the latest available rate ("current-rate
    view"); passing a date uses the rate effective on/nearest-before that
    date ("historical-rate view"). Raises CurrencyError if no rate data
    exists at all yet (never fabricates a rate)."""
    if amount is None:
        return None
    from_currency, to_currency = from_currency.upper(), to_currency.upper()
    if from_currency == to_currency:
        return amount
    for c in (from_currency, to_currency):
        if c not in SUPPORTED_CURRENCIES:
            raise CurrencyError(f"Unsupported currency '{c}'. Supported: {SUPPORTED_CURRENCIES}")

    from_info = get_rate_info(db, from_currency, on_date)
    to_info = get_rate_info(db, to_currency, on_date)
    if from_info is None or to_info is None:
        raise CurrencyError("No exchange rate data available yet — refresh rates first.")

    amount_in_idr = amount / from_info.rate if from_currency != PIVOT_CURRENCY else amount
    return amount_in_idr * to_info.rate if to_currency != PIVOT_CURRENCY else amount_in_idr


def convert_safe(db: Session, amount: float | None, from_currency: str, to_currency: str, on_date: date | None = None) -> float | None:
    """Same as convert(), but swallows CurrencyError -> None instead of
    raising — for response-shaping code that must never break a page just
    because rates haven't been fetched yet."""
    try:
        return convert(db, amount, from_currency, to_currency, on_date)
    except CurrencyError:
        return None


def format_money(amount: float | None, currency: str) -> str:
    """Backend-side formatting for text contexts (e.g. the weekly markdown
    report) where a JS Intl formatter isn't available. The frontend uses its
    own Intl.NumberFormat-based formatter for on-screen display."""
    if amount is None:
        return "—"
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    decimals = CURRENCY_DECIMALS.get(currency, 2)
    return f"{symbol}{amount:,.{decimals}f}"


# --- generic response-shaping helper -----------------------------------

# Field names, across every router in this app, that hold a money value in
# the property's base currency. Centralising this list (rather than special-
# casing each endpoint) is what lets one function convert money figures
# anywhere in a response tree.
MONEY_KEYS = {
    "gross_revenue", "net_revenue", "adr", "revpar", "avg_booking_value", "total_revenue",
    "revenue", "current_gross_revenue", "gross", "net", "target_adr", "nightly_rate",
    "median_rate", "amount", "next_30_days_revenue", "current_adr_trailing", "commission",
}
_DATE_KEYS_FOR_ROW = ("arrival_date", "booking_date", "date", "start", "effective_date")


def _row_date(obj: dict) -> date | None:
    for k in _DATE_KEYS_FOR_ROW:
        v = obj.get(k)
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v[:10])
            except ValueError:
                continue
    return None


def convert_money_in_place(db: Session, obj, from_currency: str, to_currency: str, rate_mode: str = "current") -> None:
    """Walks a response dict/list and converts every numeric value under a
    recognised money key (MONEY_KEYS) from `from_currency` to
    `to_currency`, in place. This is what every money-bearing endpoint in
    this app calls, so there is exactly one conversion code path (brief
    section 19) rather than one per page. When `rate_mode == "historical"`,
    each dict's own date-like field (arrival/booking/date/start) is used as
    the conversion date, so a booking from 8 months ago converts at the rate
    that was effective then rather than today's rate."""
    if from_currency.upper() == to_currency.upper():
        return
    if isinstance(obj, list):
        for item in obj:
            convert_money_in_place(db, item, from_currency, to_currency, rate_mode)
        return
    if not isinstance(obj, dict):
        return

    on_date = _row_date(obj) if rate_mode == "historical" else None
    for key, value in list(obj.items()):
        if key in MONEY_KEYS and isinstance(value, (int, float)) and not isinstance(value, bool):
            converted = convert_safe(db, float(value), from_currency, to_currency, on_date)
            if converted is not None:
                decimals = CURRENCY_DECIMALS.get(to_currency.upper(), 2)
                obj[key] = round(converted, decimals)
        elif isinstance(value, (dict, list)):
            convert_money_in_place(db, value, from_currency, to_currency, rate_mode)
