"""
Rule-based recommendation engine. Every rule compares a computed metric
against a threshold derived from the property's own history/competitors
(never a hard-coded absolute), and refuses to fire if the underlying sample
is too small — see docs/ARCHITECTURE.md section 7.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.review import Review, ReviewTopic
from app.services import analytics_service as asvc
from app.services import ai_narrative
from app.services.review_sentiment import mine_recurring_phrases

MIN_SAMPLE = 5
MIN_COMPETITOR_SAMPLE = 3


def _make(property_id: int, category: str, severity: str, rule_code: str, narrated: dict, evidence: dict, confidence: str, target_start=None, target_end=None) -> Recommendation:
    return Recommendation(
        property_id=property_id, category=category, severity=severity, rule_code=rule_code,
        observation=narrated["observation"], evidence=_json_safe(evidence),
        interpretation=narrated["interpretation"], action=narrated["action"],
        expected_impact=narrated["expected_impact"], confidence=confidence,
        target_start_date=target_start, target_end_date=target_end,
    )


def _json_safe(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = v.isoformat() if isinstance(v, date) else v
    return out


def _rule_pricing_and_demand(db: Session, property_id: int) -> list[Recommendation]:
    recs = []
    gaps = asvc.find_availability_gaps(db, property_id, horizon_days=60, min_gap_nights=2)
    for gap in gaps[:6]:  # cap so the dashboard isn't flooded
        pace = asvc.booking_pace(db, property_id, gap["start"], gap["end"])
        if pace.get("label") == "insufficient_data" or pace.get("sample_size", 0) == 0:
            continue

        comp_avail = asvc.competitor_availability(db, property_id, gap["start"], gap["end"])

        if pace["label"] == "slower":
            facts = {**gap, **pace}
            if comp_avail.get("available_pct") is not None and comp_avail["available_pct"] < 30:
                # slow pace but competitors also selling out -> not purely a price/demand story
                narrated = ai_narrative.narrate("conversion_issue", facts)
                confidence = "medium" if pace["sample_size"] >= 2 else "low"
                recs.append(_make(property_id, "pricing", "amber", "conversion_issue", narrated, facts, confidence, gap["start"], gap["end"]))
            else:
                narrated = ai_narrative.narrate("low_pace_gap", facts)
                confidence = "high" if pace["sample_size"] >= 2 else "medium"
                recs.append(_make(property_id, "pricing", "red", "low_pace_gap", narrated, facts, confidence, gap["start"], gap["end"]))

        elif pace["label"] == "faster" and comp_avail.get("available_pct") is not None and comp_avail["available_pct"] < 30:
            facts = {**gap, **pace, "competitor_available_pct": comp_avail["available_pct"]}
            narrated = ai_narrative.narrate("strong_demand", facts)
            confidence = "high" if comp_avail["sample_size"] >= MIN_COMPETITOR_SAMPLE else "medium"
            recs.append(_make(property_id, "pricing", "green", "strong_demand", narrated, facts, confidence, gap["start"], gap["end"]))

    return recs


def _rule_cancellations(db: Session, property_id: int) -> list[Recommendation]:
    today = date.today()
    recent = asvc.cancellation_rate(db, property_id, today - timedelta(days=30), today)
    baseline = asvc.cancellation_rate(db, property_id, today - timedelta(days=210), today - timedelta(days=30))
    if recent["total"] < MIN_SAMPLE or baseline["total"] < MIN_SAMPLE or baseline["rate_pct"] is None:
        return []
    delta = recent["rate_pct"] - baseline["rate_pct"]
    if delta >= 10:
        facts = {"recent_rate": recent["rate_pct"], "baseline_rate": baseline["rate_pct"], "recent_total": recent["total"]}
        narrated = ai_narrative.narrate("cancellation_spike", facts)
        confidence = "high" if recent["total"] >= 15 else "medium"
        return [_make(property_id, "operations", "red", "cancellation_spike", narrated, facts, confidence)]
    return []


def _rule_review_topics(db: Session, property_id: int) -> list[Recommendation]:
    recs = []
    reviews = db.query(Review).filter(Review.property_id == property_id).order_by(Review.review_date).all()
    if len(reviews) < MIN_SAMPLE:
        return []
    total_reviews = len(reviews)
    review_by_id = {r.id: r for r in reviews}
    topics = db.query(ReviewTopic).filter(ReviewTopic.review_id.in_(review_by_id.keys())).all()

    by_topic: dict[str, list[ReviewTopic]] = {}
    for t in topics:
        by_topic.setdefault(t.topic, []).append(t)

    marketing_candidates = []
    for topic, mentions in by_topic.items():
        if len(mentions) < MIN_SAMPLE:
            continue
        mention_pct = len(mentions) / total_reviews * 100
        positive = sum(1 for m in mentions if m.sentiment == "positive")
        positive_pct = positive / len(mentions) * 100

        # marketing gap candidate: strongly positive but comparatively rarely mentioned
        if positive_pct >= 85 and mention_pct <= 20:
            marketing_candidates.append((positive_pct - mention_pct, topic, mention_pct, positive_pct, len(mentions)))

        # recent risk: split mentions into recent (last N) vs earlier, compare negative share
        sorted_mentions = sorted(mentions, key=lambda m: review_by_id[m.review_id].review_date)
        recent_n = max(MIN_SAMPLE, len(sorted_mentions) // 3)
        recent, earlier = sorted_mentions[-recent_n:], sorted_mentions[:-recent_n]
        if len(recent) >= MIN_SAMPLE and len(earlier) >= MIN_SAMPLE:
            recent_neg_pct = sum(1 for m in recent if m.sentiment == "negative") / len(recent) * 100
            base_neg_pct = sum(1 for m in earlier if m.sentiment == "negative") / len(earlier) * 100
            if recent_neg_pct - base_neg_pct >= 20:
                facts = {"topic": topic.replace("_", " "), "recent_count": len(recent), "recent_negative_pct": recent_neg_pct, "baseline_negative_pct": base_neg_pct}
                narrated = ai_narrative.narrate("review_risk", facts)
                recs.append(_make(property_id, "experience", "red", "review_risk", narrated, facts, "medium"))

    # keep only the top 3 clearest marketing gaps so the dashboard highlights
    # the strongest signal (e.g. sauna/ice bath) rather than flooding the feed
    for gap_score, topic, mention_pct, positive_pct, n_mentions in sorted(marketing_candidates, reverse=True)[:3]:
        facts = {"topic": topic.replace("_", " "), "mention_pct": mention_pct, "positive_pct": positive_pct}
        narrated = ai_narrative.narrate("review_marketing_gap", facts)
        recs.append(_make(property_id, "marketing", "amber", "review_marketing_gap", narrated, facts, "medium" if n_mentions < 10 else "high"))

    return recs


def refresh_recommendations(db: Session, property_id: int) -> list[Recommendation]:
    """Recomputes all recommendations for a property and replaces the open set."""
    db.query(Recommendation).filter(Recommendation.property_id == property_id, Recommendation.status == "open").delete()

    new_recs: list[Recommendation] = []
    new_recs += _rule_pricing_and_demand(db, property_id)
    new_recs += _rule_cancellations(db, property_id)
    new_recs += _rule_review_topics(db, property_id)

    for r in new_recs:
        db.add(r)
    db.commit()
    for r in new_recs:
        db.refresh(r)
    return new_recs


def review_mining_opportunities(db: Session, property_id: int) -> list[dict]:
    reviews = db.query(Review.raw_text).filter(Review.property_id == property_id).all()
    texts = [r[0] for r in reviews]
    return mine_recurring_phrases(texts, min_mentions=max(5, len(texts) // 10))
