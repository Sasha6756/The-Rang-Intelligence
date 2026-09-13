from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.core import User
from app.models.review import Review, ReviewTopic

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

TOPIC_LABELS = {
    "cleanliness": "Cleanliness", "staff": "Staff", "service": "Service", "communication": "Communication",
    "breakfast": "Breakfast", "food": "Food", "pool": "Pool", "bedrooms": "Bedrooms", "bathrooms": "Bathrooms",
    "location": "Location", "views": "Views", "amenities": "Amenities", "check_in": "Check-in",
    "check_out": "Check-out", "noise": "Noise", "privacy": "Privacy", "value": "Value", "luxury": "Luxury",
    "comfort": "Comfort",
}


@router.get("")
def list_reviews(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reviews = (
        db.query(Review)
        .filter(Review.property_id == current_user.property_id)
        .order_by(Review.review_date.desc())
        .limit(200)
        .all()
    )
    return [
        {"id": r.id, "source": r.source, "review_date": r.review_date, "rating": r.rating,
         "guest_country": r.guest_country, "raw_text": r.raw_text, "sentiment_score": r.sentiment_score}
        for r in reviews
    ]


@router.get("/topic-summary")
def topic_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    review_ids = [r.id for r in db.query(Review.id).filter(Review.property_id == current_user.property_id).all()]
    total_reviews = len(review_ids)
    if not review_ids:
        return []
    topics = db.query(ReviewTopic).filter(ReviewTopic.review_id.in_(review_ids)).all()

    by_topic: dict[str, dict] = {}
    for t in topics:
        bucket = by_topic.setdefault(t.topic, {"positive": 0, "negative": 0, "neutral": 0, "mentions": 0})
        bucket[t.sentiment] += 1
        bucket["mentions"] += 1

    result = []
    for topic, counts in by_topic.items():
        positive_pct = round(counts["positive"] / counts["mentions"] * 100, 1) if counts["mentions"] else 0
        result.append({
            "topic": topic, "label": TOPIC_LABELS.get(topic, topic.title()),
            "mentions": counts["mentions"],
            "mention_share_pct": round(counts["mentions"] / total_reviews * 100, 1),
            "positive_pct": positive_pct,
            "negative": counts["negative"], "positive": counts["positive"], "neutral": counts["neutral"],
        })
    return sorted(result, key=lambda r: -r["mentions"])
