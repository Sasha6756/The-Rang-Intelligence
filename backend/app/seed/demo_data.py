"""
Generates realistic, clearly-labelled DEMO DATA for The Rang Uluwatu so the
product is usable immediately. Run with:

    python -m app.seed.demo_data

Idempotent: skips generation if a demo property already exists (delete the
database file to start over, or pass --force).
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta

from app.db.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.core import Property, User, UserRole, Channel, Guest
from app.models.booking import Reservation, ReservationStatus
from app.models.review import Review, ReviewTopic
from app.models.competitor import Competitor, CompetitorRate
from app.services.review_sentiment import analyze_review

random.seed(42)

TODAY = date.today()
HISTORY_START = TODAY - timedelta(days=760)   # ~2 years of history for YoY comparables
FUTURE_END = TODAY + timedelta(days=120)      # 4 months of forward calendar

COUNTRIES = [
    ("Australia", 0.30), ("Singapore", 0.16), ("United States", 0.12), ("United Kingdom", 0.10),
    ("Indonesia", 0.08), ("South Korea", 0.06), ("Japan", 0.05), ("Germany", 0.05),
    ("Canada", 0.04), ("Netherlands", 0.04),
]
CHANNEL_WEIGHTS = [("Airbnb", 0.40), ("Booking.com", 0.34), ("Direct", 0.26)]
LOS_CHOICES = [2, 3, 4, 5, 6, 7, 10, 14]
LOS_WEIGHTS = [0.10, 0.20, 0.22, 0.18, 0.10, 0.10, 0.06, 0.04]

# Engineered near-term scenarios so the recommendation engine has something
# concrete to find on first load (see docs/ARCHITECTURE.md section 7).
GAP_WINDOW = (TODAY + timedelta(days=26), TODAY + timedelta(days=31))   # left empty -> low_pace_gap / conversion_issue
HOT_WINDOW = (TODAY + timedelta(days=52), TODAY + timedelta(days=58))   # filled near-full -> strong_demand
CANCEL_SPIKE_SINCE = TODAY - timedelta(days=25)                          # recent cancellation-rate spike


def weighted_choice(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


def daterange(start: date, end: date):
    d = start
    while d < end:
        yield d
        d += timedelta(days=1)


def seasonal_base_occupancy(d: date) -> float:
    """Uluwatu high season ~ Jul-Aug & Dec-Jan; shoulder Jun/Sep/Mar; low Feb/Apr/May/Oct/Nov."""
    m = d.month
    if m in (7, 8, 12) or (m == 1 and d.day <= 20):
        return 0.80
    if m in (6, 9, 3):
        return 0.62
    return 0.45


def seasonal_adr(d: date) -> float:
    base = 1450
    m = d.month
    if m in (7, 8, 12) or (m == 1 and d.day <= 20):
        base *= 1.28
    elif m in (6, 9, 3):
        base *= 1.05
    else:
        base *= 0.88
    if d.weekday() in (4, 5):
        base *= 1.08
    base *= random.uniform(0.93, 1.07)
    return round(base, 0)


def sample_lead_time(is_last_minute: bool) -> int:
    if is_last_minute:
        return random.randint(1, 10)
    return max(1, int(random.gauss(48, 30)))


def month_bounds(d: date):
    start = d.replace(day=1)
    nxt = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    return start, nxt


def generate_booking_windows() -> list[dict]:
    """Direct occupancy-quota based placement — avoids the bias a pure random-
    walk/renewal process introduces and gives predictable, tunable occupancy."""
    occupied: dict[date, bool] = {}
    bookings: list[dict] = []

    month = HISTORY_START.replace(day=1)
    while month < FUTURE_END:
        m_start, m_end = month_bounds(month)
        window_start, window_end = max(m_start, HISTORY_START), min(m_end, FUTURE_END)
        n_days = (window_end - window_start).days
        if n_days <= 0:
            month = m_end
            continue

        mid = window_start + timedelta(days=n_days // 2)
        occ_target = seasonal_base_occupancy(mid)
        if window_start >= TODAY:
            days_out = (window_start - TODAY).days
            occ_target *= max(0.30, 1 - days_out / 160)  # future months are naturally thinner (less lead time elapsed)

        target_nights = int(n_days * occ_target)
        attempts = 0
        occupied_in_window = sum(1 for d in daterange(window_start, window_end) if occupied.get(d))

        while occupied_in_window < target_nights and attempts < 400:
            attempts += 1
            start_day = window_start + timedelta(days=random.randint(0, n_days - 1))
            if occupied.get(start_day):
                continue
            nights = weighted_choice(list(zip(LOS_CHOICES, LOS_WEIGHTS)))
            arrival, departure = start_day, start_day + timedelta(days=nights)
            if any(occupied.get(arrival + timedelta(days=i)) for i in range(nights)):
                continue

            is_last_minute = random.random() < 0.22
            lead_time = sample_lead_time(is_last_minute)
            if arrival > TODAY:
                lead_time = min(lead_time, max((arrival - TODAY).days, 0))
            booking_date = min(arrival - timedelta(days=lead_time), TODAY)

            for i in range(nights):
                occupied[arrival + timedelta(days=i)] = True
            bookings.append(dict(arrival=arrival, departure=departure, nights=nights, booking_date=booking_date, is_last_minute=is_last_minute))
            occupied_in_window += min(nights, (window_end - arrival).days)

        month = m_end

    # --- engineered scenario: leave GAP_WINDOW completely empty -------------
    g0, g1 = GAP_WINDOW
    bookings = [b for b in bookings if not (b["arrival"] < g1 and b["departure"] > g0)]
    for d in daterange(g0, g1):
        occupied[d] = False

    # --- engineered scenario: fill HOT_WINDOW to near-full -------------------
    h0, h1 = HOT_WINDOW
    for d in daterange(h0, h1):
        if occupied.get(d):
            continue
        nights = random.choice([1, 2, 3])
        if all(not occupied.get(d + timedelta(days=i)) for i in range(nights)):
            lead_time = min(sample_lead_time(False), max((d - TODAY).days, 0))
            booking_date = min(d - timedelta(days=lead_time), TODAY)
            for i in range(nights):
                occupied[d + timedelta(days=i)] = True
            bookings.append(dict(arrival=d, departure=d + timedelta(days=nights), nights=nights, booking_date=booking_date, is_last_minute=False))

    return sorted(bookings, key=lambda b: b["arrival"])


REVIEW_TEMPLATES_POSITIVE = [
    "The {view} was absolutely {adj} - we watched the sunset from the pool every single evening and it never got old.",
    "Staff were incredibly {adj}, especially the villa manager who anticipated everything we needed.",
    "The infinity pool and in-pool bar made this the most {adj} stay of our trip. Breakfast was simple but nicely presented.",
    "Cliffside location near Suluban surf is unbeatable. The sunset views from the villa are {adj}.",
    "We used the ice bath and sauna every day - genuinely a highlight, though it's barely mentioned in the listing.",
    "Communication before arrival was {adj} and check-in was seamless.",
    "Five bedrooms meant the whole group could travel together comfortably. The staff service was {adj}.",
    "Cleanliness was spotless throughout our stay, and the bathrooms felt like a five-star hotel.",
    "Watched an incredible sunset from the sunken lounge with cocktails - unforgettable evening.",
    "The villa felt private and quiet despite being close to Single Fin. Staff, food and service were all {adj}.",
]
REVIEW_TEMPLATES_NEGATIVE = [
    "Breakfast was underwhelming for a villa at this price point - felt like an afterthought.",
    "Communication was slow when we tried to arrange an early check-in.",
    "We noticed some noise from a nearby property in the evenings, which was disappointing given the price.",
    "Water pressure in one of the bathrooms was weak during our stay.",
    "Staff response time to our WhatsApp messages was slower than we expected for a luxury villa.",
]
ADJ = ["stunning", "incredible", "amazing", "beautiful", "exceptional", "outstanding", "wonderful"]


def make_review_text(positive: bool, force_topic: str | None = None) -> str:
    if force_topic == "communication_negative":
        return random.choice([
            "Communication with the team was slow and messages went unanswered for hours before check-in.",
            "We had to follow up twice on WhatsApp before getting a reply about our arrival time - communication needs work.",
        ])
    template = random.choice(REVIEW_TEMPLATES_POSITIVE if positive else REVIEW_TEMPLATES_NEGATIVE)
    return template.format(view=random.choice(["ocean view", "sunset", "cliffside outlook"]), adj=random.choice(ADJ))


def generate():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Property).filter(Property.is_demo == True).first()  # noqa: E712
        if existing and "--force" not in sys.argv:
            print(f"Demo property already exists (id={existing.id}). Delete the database file or pass --force to regenerate.")
            return

        for name, commission, is_ota in [("Booking.com", 15.0, True), ("Airbnb", 3.0, True), ("Direct", 0.0, False), ("Other", 0.0, True)]:
            if not db.query(Channel).filter(Channel.name == name).first():
                db.add(Channel(name=name, default_commission_pct=commission, is_ota=is_ota))
        db.commit()

        prop = Property(
            name="The Rang Uluwatu (DEMO)", address="Uluwatu, Bali, Indonesia", bedrooms=5,
            currency="USD", timezone="Asia/Makassar", target_occupancy_pct=65.0, target_adr=1450.0, is_demo=True,
        )
        db.add(prop)
        db.flush()

        db.add(User(property_id=prop.id, email="demo@therang.com", hashed_password=hash_password("demo1234"), name="Demo Owner", role=UserRole.OWNER))
        db.commit()

        channels_by_name = {c.name: c for c in db.query(Channel).all()}

        # ---- Reservations ----------------------------------------------------
        windows = generate_booking_windows()
        booking_count = 0
        for i, b in enumerate(windows):
            channel = channels_by_name[weighted_choice(CHANNEL_WEIGHTS)]
            adults = random.choice([2, 2, 4, 4, 6, 8, 10])
            children = random.choice([0, 0, 0, 1, 2])
            nightly_rate = seasonal_adr(b["arrival"])
            gross_revenue = round(nightly_rate * b["nights"] * (0.94 if b["nights"] >= 7 else 1.0), 2)
            commission = round(gross_revenue * channel.default_commission_pct / 100, 2)

            status, cancellation_date = ReservationStatus.CONFIRMED, None
            base_cancel_prob = 0.24 if b["booking_date"] >= CANCEL_SPIKE_SINCE else 0.07
            if random.random() < base_cancel_prob:
                status = ReservationStatus.CANCELLED
                max_gap = max(1, (b["arrival"] - b["booking_date"]).days // 2)
                cancellation_date = b["booking_date"] + timedelta(days=random.randint(1, max_gap))

            guest = Guest(property_id=prop.id, name="", country=weighted_choice(COUNTRIES), is_repeat=random.random() < 0.12)
            db.add(guest)
            db.flush()

            db.add(Reservation(
                property_id=prop.id, channel_id=channel.id, guest_id=guest.id,
                external_ref=f"DEMO-{i:05d}", booking_date=b["booking_date"],
                arrival_date=b["arrival"], departure_date=b["departure"], nights=b["nights"],
                adults=adults, children=children, gross_revenue=gross_revenue, commission=commission,
                net_revenue=round(gross_revenue - commission, 2), currency="USD",
                status=status, cancellation_date=cancellation_date,
            ))
            booking_count += 1
            if booking_count % 100 == 0:
                db.commit()

        db.commit()
        print(f"Inserted {booking_count} demo reservations.")

        # ---- Competitors + rates ----------------------------------------------
        competitor_specs = [
            ("Villa Sundara Cliff", 5, True, True, 4.8, 210),
            ("Cliffhouse Uluwatu", 4, True, False, 4.6, 150),
            ("Blue Horizon Villa", 5, True, False, 4.7, 95),
            ("The Surf Sanctuary", 6, True, True, 4.9, 180),
            ("Uluwatu Point Villa", 5, False, False, 4.5, 60),
            ("Sanka Cliffside Estate", 5, True, True, 4.7, 130),
        ]
        competitors = []
        for name, bedrooms, pool, sauna, score, count in competitor_specs:
            c = Competitor(property_id=prop.id, name=name, bedrooms=bedrooms, location="Uluwatu",
                            has_pool=pool, has_sauna=sauna, ocean_view=True, review_score=score, review_count=count)
            db.add(c)
            competitors.append(c)
        db.commit()

        h0, h1 = HOT_WINDOW
        g0, g1 = GAP_WINDOW
        for cursor in daterange(TODAY, FUTURE_END):
            in_hot, in_gap = h0 <= cursor < h1, g0 <= cursor < g1
            for c in competitors:
                if in_hot:
                    available, rate = random.random() < 0.15, seasonal_adr(cursor) * random.uniform(0.85, 1.0)
                elif in_gap:
                    available, rate = random.random() < 0.85, seasonal_adr(cursor) * random.uniform(0.75, 0.9)
                else:
                    available, rate = random.random() < 0.55, seasonal_adr(cursor) * random.uniform(0.85, 1.05)
                db.add(CompetitorRate(competitor_id=c.id, date=cursor, nightly_rate=round(rate, 0), available=available, min_stay=random.choice([1, 2, 3])))
        db.commit()
        print("Inserted competitor rate observations.")

        # ---- Reviews -----------------------------------------------------------
        review_count = 0
        candidate_days = list(daterange(HISTORY_START, TODAY))
        review_dates = sorted(random.sample(candidate_days, k=min(110, len(candidate_days))))
        for i, rdate in enumerate(review_dates):
            is_recent = i >= len(review_dates) - 15
            force_negative_comm = is_recent and random.random() < 0.55  # engineered recent negative trend
            positive = random.random() < 0.90 and not force_negative_comm
            text_parts = [make_review_text(positive)]
            if random.random() < 0.45:
                text_parts.append(make_review_text(True))
            if random.random() < 0.08:
                text_parts.append("The sauna and ice bath were an unexpected highlight of the trip.")
            if force_negative_comm:
                text_parts.append(make_review_text(False, force_topic="communication_negative"))
            raw_text = " ".join(text_parts)

            source = weighted_choice([("Airbnb", 0.4), ("Booking.com", 0.35), ("Google", 0.15), ("Direct", 0.10)])
            rating = round(random.uniform(4.4, 5.0) if positive else random.uniform(3.2, 4.2), 1)
            sentiment_score, topics = analyze_review(raw_text)
            review = Review(property_id=prop.id, source=source, review_date=rdate, rating=rating,
                             guest_country=weighted_choice(COUNTRIES), raw_text=raw_text, sentiment_score=sentiment_score)
            db.add(review)
            db.flush()
            for topic, sentiment, snippet in topics:
                db.add(ReviewTopic(review_id=review.id, topic=topic, sentiment=sentiment, snippet=snippet))
            review_count += 1

        db.commit()
        print(f"Inserted {review_count} demo reviews.")
        print("\nDemo login: demo@therang.com / demo1234")

    finally:
        db.close()


if __name__ == "__main__":
    generate()
