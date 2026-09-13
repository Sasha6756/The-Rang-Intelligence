from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.models.competitor import Competitor

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


class CompetitorIn(BaseModel):
    name: str
    bedrooms: int = 0
    location: str = "Uluwatu"
    has_pool: bool = True
    has_sauna: bool = False
    ocean_view: bool = True
    review_score: float | None = None
    review_count: int = 0
    listing_url: str = ""
    notes: str = ""


@router.get("")
def list_competitors(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comps = db.query(Competitor).filter(Competitor.property_id == current_user.property_id).all()
    return [
        {"id": c.id, "name": c.name, "bedrooms": c.bedrooms, "location": c.location, "has_pool": c.has_pool,
         "has_sauna": c.has_sauna, "ocean_view": c.ocean_view, "review_score": c.review_score,
         "review_count": c.review_count, "listing_url": c.listing_url, "notes": c.notes}
        for c in comps
    ]


@router.post("")
def create_competitor(payload: CompetitorIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comp = Competitor(property_id=current_user.property_id, **payload.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return {"id": comp.id}


@router.delete("/{competitor_id}")
def delete_competitor(competitor_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comp = db.get(Competitor, competitor_id)
    if comp and comp.property_id == current_user.property_id:
        db.delete(comp)
        db.commit()
    return {"ok": True}
