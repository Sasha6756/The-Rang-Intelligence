"""
Lexicon-based review topic tagging + sentiment scoring.

Deliberately rule-based rather than an LLM call for the MVP: it is
deterministic, free, instant, auditable, and good enough to power topic-level
percentages and review mining. The AI narrative layer (ai_narrative.py) is
what turns the resulting numbers into prose — this module only ever produces
numbers and tagged snippets.
"""
from __future__ import annotations

import re

TOPICS: dict[str, list[str]] = {
    "cleanliness": ["clean", "spotless", "tidy", "dust", "dirty", "housekeeping"],
    "staff": ["staff", "butler", "host", "team", "manager", "villa manager"],
    "service": ["service", "attentive", "responsive", "helpful", "accommodating"],
    "communication": ["communication", "responded", "reply", "whatsapp", "message"],
    "breakfast": ["breakfast", "brekkie"],
    "food": ["food", "meal", "dinner", "chef", "cuisine"],
    "pool": ["pool", "infinity pool", "swim"],
    "bedrooms": ["bedroom", "bed", "mattress", "linen"],
    "bathrooms": ["bathroom", "shower", "bathtub"],
    "location": ["location", "cliffside", "uluwatu", "surf", "single fin", "suluban"],
    "views": ["view", "sunset", "ocean view", "vista"],
    "amenities": ["sauna", "ice bath", "gym", "amenities", "facilities"],
    "check_in": ["check-in", "check in", "arrival", "welcome"],
    "check_out": ["check-out", "check out", "departure"],
    "noise": ["noise", "loud", "quiet"],
    "privacy": ["privacy", "private"],
    "value": ["value", "price", "worth", "expensive", "overpriced"],
    "luxury": ["luxury", "luxurious", "high-end", "premium", "opulent"],
    "comfort": ["comfort", "comfortable", "cozy"],
}

POSITIVE_WORDS = {
    "amazing", "beautiful", "stunning", "incredible", "excellent", "perfect", "wonderful",
    "fantastic", "gorgeous", "lovely", "great", "best", "outstanding", "impeccable",
    "attentive", "spotless", "helpful", "friendly", "unforgettable", "flawless", "exceptional",
}
NEGATIVE_WORDS = {
    "dirty", "slow", "rude", "poor", "disappointing", "broken", "overpriced", "noisy",
    "uncomfortable", "unresponsive", "cold", "stained", "smell", "bug", "mosquito", "leak",
}


def _sentence_sentiment(text: str) -> tuple[str, float]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    if pos == 0 and neg == 0:
        return "neutral", 0.0
    score = (pos - neg) / max(pos + neg, 1)
    label = "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral")
    return label, score


def analyze_review(raw_text: str) -> tuple[float, list[tuple[str, str, str]]]:
    """Returns (overall_sentiment_score -1..1, [(topic, sentiment, snippet), ...])."""
    sentences = re.split(r"(?<=[.!?])\s+", raw_text.strip())
    overall_label, overall_score = _sentence_sentiment(raw_text)

    topic_hits: list[tuple[str, str, str]] = []
    lower_text = raw_text.lower()
    for topic, keywords in TOPICS.items():
        for kw in keywords:
            if kw in lower_text:
                # find the sentence containing the keyword for a snippet + local sentiment
                snippet_sentence = next((s for s in sentences if kw in s.lower()), raw_text[:140])
                sentiment, _ = _sentence_sentiment(snippet_sentence)
                if sentiment == "neutral":
                    sentiment = overall_label  # fall back to overall tone
                topic_hits.append((topic, sentiment, snippet_sentence.strip()[:300]))
                break  # one hit per topic per review is enough for topic-level stats

    return round(overall_score, 3), topic_hits


COMMON_PHRASES = [
    "beautiful sunset", "amazing sunset", "incredible sunset", "sunset was", "watched the sunset",
    "infinity pool", "ice bath", "the sauna", "surf access", "cliffside", "villa staff",
]


def mine_recurring_phrases(review_texts: list[str], min_mentions: int = 5) -> list[dict]:
    """Very simple recurring-phrase mining used for the 'review mining' marketing-opportunity feature.

    Counts occurrences of a fixed set of experience-relevant phrases across all
    reviews. This is intentionally conservative (a known phrase list, not
    open-ended NLP) so it never invents a theme that isn't actually there.
    """
    results = []
    lower_texts = [t.lower() for t in review_texts]
    for phrase in COMMON_PHRASES:
        count = sum(1 for t in lower_texts if phrase in t)
        if count >= min_mentions:
            results.append({"phrase": phrase, "mentions": count, "share_of_reviews": round(count / max(len(review_texts), 1) * 100, 1)})
    return sorted(results, key=lambda r: -r["mentions"])
