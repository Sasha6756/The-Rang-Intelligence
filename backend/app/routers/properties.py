from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User, Property
from app.schemas.property import PropertyOut, PropertyUpdate

router = APIRouter(prefix="/api/property", tags=["property"])


@router.get("", response_model=PropertyOut)
def get_property(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.get(Property, current_user.property_id)


@router.put("", response_model=PropertyOut)
def update_property(
    payload: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prop = db.get(Property, current_user.property_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.commit()
    db.refresh(prop)
    return prop
