"""
Turns already-computed structured facts into the plain-English
OBSERVATION / INTERPRETATION / ACTION / EXPECTED IMPACT text shown on the
dashboard. This module NEVER computes a metric — every number it uses is
passed in from analytics_service / recommendation_engine.

Two interchangeable backends behind one function, `narrate(rule_code, facts)`:
  - deterministic template composer (default; zero config, always available)
  - Claude API narrator (used only if ANTHROPIC_API_KEY is set), which is
    given the facts as the ONLY allowed source of truth and instructed never
    to introduce a number that isn't in them. If the API call fails for any
    reason, we silently fall back to the deterministic templates so the
    product never breaks because of an AI outage.
"""
from __future__ import annotations

from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Deterministic templates — one per rule_code. Each returns the fixed
# OBSERVATION/INTERPRETATION/ACTION/EXPECTED_IMPACT structure from the brief.
# ---------------------------------------------------------------------------

def _tpl_low_pace_gap(f: dict) -> dict:
    return {
        "observation": (
            f"{f['start']:%-d %b} – {f['end']:%-d %b} ({f['nights']} nights) is currently unbooked. "
            f"Booking pace for this window is {f['delta_pts']:+.0f} points {'behind' if f['delta_pts'] < 0 else 'ahead of'} "
            f"the historical average at this lead time ({f['days_out']} days out)."
        ),
        "interpretation": (
            f"Your competitor set is priced with a median comparable rate; "
            f"{'this stretch is under-converting relative to how it normally fills at this point.' if f['delta_pts'] < 0 else 'demand looks healthy for these dates.'}"
        ),
        "action": (
            "Consider a bounded rate reduction (roughly 5-10%) for these specific dates and review whether a "
            "minimum-stay restriction is excluding shorter bookings, rather than discounting broadly."
        ),
        "expected_impact": "Directionally higher booking probability for this window; exact conversion lift cannot be quantified without price-elasticity history.",
    }


def _tpl_strong_demand(f: dict) -> dict:
    return {
        "observation": (
            f"{f['start']:%-d %b} – {f['end']:%-d %b} is booking faster than its historical average "
            f"({f['delta_pts']:+.0f} points at {f['days_out']} days out), and only {f['competitor_available_pct']:.0f}% "
            f"of tracked comparable villas show availability for overlapping dates."
        ),
        "interpretation": "Demand for this window appears to exceed typical supply in your comparable set.",
        "action": "Hold or increase ADR for these dates rather than discounting; do not run promotions here.",
        "expected_impact": "Potential to capture additional margin without materially reducing booking probability, given constrained competitor availability.",
    }


def _tpl_conversion_issue(f: dict) -> dict:
    return {
        "observation": (
            f"{f['start']:%-d %b} – {f['end']:%-d %b} is pacing {f['delta_pts']:.0f} points behind its historical "
            f"average at this lead time, while comparable-villa availability is not unusually low."
        ),
        "interpretation": "Price and market demand don't fully explain the slow pace — this looks more like a listing conversion or visibility issue than a demand problem.",
        "action": "Review listing photos, description and search ranking factors for this period before considering a price cut.",
        "expected_impact": "Cannot be quantified from booking data alone — flagged for manual listing review.",
    }


def _tpl_cancellation_spike(f: dict) -> dict:
    return {
        "observation": (
            f"Cancellation rate for bookings made in the last 30 days is {f['recent_rate']:.0f}%, "
            f"versus a {f['baseline_rate']:.0f}% trailing baseline."
        ),
        "interpretation": "This is a meaningful step up and is worth investigating — common causes include a promotion's terms, deposit/refund policy, or a specific channel.",
        "action": "Review recent cancellations for a common channel, promotion or booking pattern before making policy changes.",
        "expected_impact": "Reducing avoidable cancellations directly protects realised revenue.",
    }


def _tpl_review_marketing_gap(f: dict) -> dict:
    return {
        "observation": (
            f"'{f['topic']}' is mentioned in {f['mention_pct']:.0f}% of reviews with {f['positive_pct']:.0f}% positive sentiment "
            f"when mentioned — strongly positive but rarely brought up."
        ),
        "interpretation": "This is a differentiated experience element that isn't being surfaced in marketing or the listing.",
        "action": f"Feature {f['topic']} more prominently in the listing description and create dedicated photo/video content around it.",
        "expected_impact": "Marketing-content changes based on guest feedback have historically supported stronger positioning; no direct booking-lift figure is available yet.",
    }


def _tpl_review_risk(f: dict) -> dict:
    return {
        "observation": (
            f"'{f['topic']}' sentiment among the last {f['recent_count']} mentions is "
            f"{f['recent_negative_pct']:.0f}% negative, versus {f['baseline_negative_pct']:.0f}% previously."
        ),
        "interpretation": "This looks like an emerging operational issue rather than noise, given the sample size.",
        "action": f"Investigate recent guest feedback about {f['topic']} with the villa team and address the root cause.",
        "expected_impact": "Addressing recurring negative feedback protects review scores and future conversion.",
    }


TEMPLATES = {
    "low_pace_gap": _tpl_low_pace_gap,
    "strong_demand": _tpl_strong_demand,
    "conversion_issue": _tpl_conversion_issue,
    "cancellation_spike": _tpl_cancellation_spike,
    "review_marketing_gap": _tpl_review_marketing_gap,
    "review_risk": _tpl_review_risk,
}


def _narrate_with_llm(rule_code: str, facts: dict, template_result: dict) -> dict | None:
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system = (
            "You are a revenue-management analyst writing one short recommendation card for a luxury villa "
            "owner. You are given FACTS (already-computed numbers) and a DRAFT written from those same facts. "
            "Rewrite the draft to be clearer and more natural, in the same OBSERVATION/INTERPRETATION/ACTION/"
            "EXPECTED_IMPACT structure. You MUST NOT introduce any number, percentage, date or claim that is not "
            "present in FACTS or DRAFT. If you are unsure, keep the draft's wording. Reply as JSON with keys "
            "observation, interpretation, action, expected_impact."
        )
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": f"FACTS: {facts}\n\nDRAFT: {template_result}"}],
        )
        import json
        text = message.content[0].text
        return json.loads(text)
    except Exception:
        return None  # never let an AI outage break the product — fall back silently


def narrate(rule_code: str, facts: dict) -> dict:
    template_fn = TEMPLATES.get(rule_code)
    if not template_fn:
        raise ValueError(f"Unknown rule_code '{rule_code}'")
    draft = template_fn(facts)
    if settings.ANTHROPIC_API_KEY:
        improved = _narrate_with_llm(rule_code, facts, draft)
        if improved and all(k in improved for k in ("observation", "interpretation", "action", "expected_impact")):
            return improved
    return draft
