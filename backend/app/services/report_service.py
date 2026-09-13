"""Weekly AI Intelligence report — assembled entirely from already-computed
deterministic metrics + the recommendation engine's output. See brief section 24."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.core import Property
from app.models.recommendation import Recommendation
from app.services import analytics_service as asvc
from app.services import currency_service as csvc


def generate_weekly_report(db: Session, property_id: int) -> dict:
    prop = db.get(Property, property_id)
    today = date.today()
    week_start, week_end = today - timedelta(days=7), today
    prior_week_start = week_start - timedelta(days=7)

    this_week = asvc.core_metrics(db, property_id, week_start, week_end)
    last_week = asvc.core_metrics(db, property_id, prior_week_start, week_start)

    occ_delta = this_week["occupancy_pct"] - last_week["occupancy_pct"]
    revenue_delta_pct = (
        round((this_week["gross_revenue"] - last_week["gross_revenue"]) / last_week["gross_revenue"] * 100, 1)
        if last_week["gross_revenue"] else None
    )

    open_recs = (
        db.query(Recommendation)
        .filter(Recommendation.property_id == property_id, Recommendation.status == "open")
        .order_by(Recommendation.severity.desc())
        .all()
    )

    next_7 = asvc.core_metrics(db, property_id, today, today + timedelta(days=7))

    top_actions = []
    for r in open_recs[:5]:
        prefix = f"[{r.target_start_date:%d %b}–{r.target_end_date:%d %b}] " if r.target_start_date and r.target_end_date else ""
        top_actions.append({
            "category": r.category, "action": prefix + r.action,
            "expected_impact": r.expected_impact, "confidence": r.confidence, "severity": r.severity,
        })

    return {
        "property_name": prop.name,
        "currency": prop.currency,
        "generated_at": today,
        "period": {"start": week_start, "end": week_end},
        "performance": this_week,
        "previous_week": last_week,
        "occupancy_change_pts": round(occ_delta, 1),
        "revenue_change_pct": revenue_delta_pct,
        "biggest_opportunity": next((r for r in open_recs if r.severity == "green"), None),
        "biggest_risk": next((r for r in open_recs if r.severity == "red"), None),
        "next_7_days_forecasted_occupancy_pct": next_7["occupancy_pct"],
        "top_actions": top_actions,
        "all_open_recommendations_count": len(open_recs),
    }


def render_markdown(report: dict) -> str:
    p = report["performance"]
    currency = report.get("currency", "")
    fmt = lambda v: csvc.format_money(v, currency) if currency else (f"{v:,.0f}" if v is not None else "—")
    lines = [
        f"# {report['property_name']} — Weekly Intelligence",
        f"_Generated {report['generated_at']:%d %b %Y} — covering {report['period']['start']:%d %b} to {report['period']['end']:%d %b}_",
        "",
        "## Performance",
        f"- Occupancy: {p['occupancy_pct']}% ({report['occupancy_change_pts']:+.1f} pts vs prior week)",
        f"- ADR: {fmt(p['adr'])}",
        f"- Gross revenue: {fmt(p['gross_revenue'])}"
        + (f" ({report['revenue_change_pct']:+.1f}% vs prior week)" if report["revenue_change_pct"] is not None else ""),
        f"- RevPAR: {fmt(p['revpar'])}",
        "",
        "## Biggest opportunity",
        (report["biggest_opportunity"].action if report["biggest_opportunity"] else "No standout opportunity flagged this week."),
        "",
        "## Biggest risk",
        (report["biggest_risk"].action if report["biggest_risk"] else "No red-flag risk currently open."),
        "",
        f"## Next 7 days\nForecasted occupancy based on bookings on the books: {report['next_7_days_forecasted_occupancy_pct']}%",
        "",
        "## Top actions this week",
    ]
    for i, a in enumerate(report["top_actions"], 1):
        lines.append(f"{i}. **[{a['category']}, confidence: {a['confidence']}]** {a['action']} — _{a['expected_impact']}_")
    if not report["top_actions"]:
        lines.append("No open recommendations — refresh recommendations from the Recommendations page.")
    return "\n".join(lines)
