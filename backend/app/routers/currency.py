from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.services import currency_service as csvc

router = APIRouter(prefix="/api/currency", tags=["currency"])


@router.get("/rates")
def get_rates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Latest known rate for every supported currency, whether it's stale,
    and the property's base/default-display currency — backs the Settings
    'Currency' panel and the top-bar rate badge."""
    prop = db.get(Property, current_user.property_id)
    status = csvc.get_status(db)
    status["property_base_currency"] = prop.currency
    status["property_default_display_currency"] = prop.default_display_currency or prop.currency
    status["supported_currencies"] = csvc.SUPPORTED_CURRENCIES
    return status


@router.post("/refresh")
def refresh(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manually trigger a rate refresh ('Refresh rates' button in Settings).
    Runs the same code path as the daily scheduled refresh."""
    return csvc.refresh_rates(db)


@router.get("/convert")
def convert_endpoint(
    amount: float,
    from_currency: str,
    to_currency: str,
    on_date: date | None = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One-off conversion utility — used by the frontend's currency-selector
    smoke test and available for ad-hoc lookups."""
    try:
        result = csvc.convert(db, amount, from_currency.upper(), to_currency.upper(), on_date)
    except csvc.CurrencyError as e:
        raise HTTPException(400, str(e))
    return {
        "amount": amount, "from_currency": from_currency.upper(), "to_currency": to_currency.upper(),
        "date": on_date, "result": result,
    }
