from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.models.recommendation import Recommendation
from app.services import recommendation_engine as svc

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _serialize(r: Recommendation) -> dict:
    return {
        "id": r.id, "category": r.category, "severity": r.severity, "rule_code": r.rule_code,
        "observation": r.observation, "evidence": r.evidence, "interpretation": r.interpretation,
        "action": r.action, "expected_impact": r.expected_impact, "confidence": r.confidence,
        "status": r.status, "target_start_date": r.target_start_date, "target_end_date": r.target_end_date,
        "created_at": r.created_at,
    }


@router.post("/refresh")
def refresh(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recs = svc.refresh_recommendations(db, current_user.property_id)
    return [_serialize(r) for r in recs]


@router.get("")
def list_recommendations(status: str = "open", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Recommendation).filter(Recommendation.property_id == current_user.property_id)
    if status != "all":
        q = q.filter(Recommendation.status == status)
    recs = q.order_by(Recommendation.severity.desc(), Recommendation.created_at.desc()).all()
    return [_serialize(r) for r in recs]


@router.post("/{rec_id}/dismiss")
def dismiss(rec_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.get(Recommendation, rec_id)
    if rec and rec.property_id == current_user.property_id:
        rec.status = "dismissed"
        db.commit()
    return {"ok": True}


@router.post("/{rec_id}/action")
def mark_actioned(rec_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = db.get(Recommendation, rec_id)
    if rec and rec.property_id == current_user.property_id:
        rec.status = "actioned"
        db.commit()
    return {"ok": True}


@router.get("/review-mining")
def review_mining(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.review_mining_opportunities(db, current_user.property_id)
