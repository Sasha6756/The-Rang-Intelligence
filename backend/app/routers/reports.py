from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.services import report_service as svc
from app.services import currency_service as csvc

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/weekly")
def weekly_report(
    currency: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = svc.generate_weekly_report(db, current_user.property_id)
    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, report, prop.currency, display, "current")
        report["currency"] = display
    for key in ("biggest_opportunity", "biggest_risk"):
        rec = report[key]
        report[key] = None if rec is None else {
            "observation": rec.observation, "action": rec.action, "expected_impact": rec.expected_impact,
            "confidence": rec.confidence, "severity": rec.severity,
        }
    return report


@router.get("/weekly.md")
def weekly_report_markdown(
    currency: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = svc.generate_weekly_report(db, current_user.property_id)
    prop = db.get(Property, current_user.property_id)
    display = (currency or prop.currency).upper()
    if display != prop.currency.upper():
        csvc.convert_money_in_place(db, report, prop.currency, display, "current")
        report["currency"] = display
    for key in ("biggest_opportunity", "biggest_risk"):
        rec = report[key]
        report[key] = None if rec is None else rec  # keep object; render_markdown reads .action
    md = svc.render_markdown(report)
    return Response(content=md, media_type="text/markdown")
