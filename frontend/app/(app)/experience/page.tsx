"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function ExperiencePage() {
  const [topics, setTopics] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [mining, setMining] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/api/reviews/topic-summary").then(setTopics);
    apiGet("/api/reviews").then((r: any[]) => setReviews(r.slice(0, 15)));
    apiGet("/api/recommendations/review-mining").then(setMining);
  }, []);

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-1">Experience</h1>
      <p className="text-muted text-sm mb-8">Reviews classified into topics with sentiment — the same numbers behind the marketing and operations recommendations.</p>

      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3 mb-10">
        {topics.map((t) => (
          <div key={t.topic} className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-charcoal">{t.label}</span>
              <span className={`font-serif text-lg ${t.positive_pct >= 80 ? "text-sage" : t.positive_pct >= 60 ? "text-bronze" : "text-terracotta"}`}>
                {t.positive_pct}%
              </span>
            </div>
            <div className="text-[11px] text-muted mt-1">mentioned in {t.mention_share_pct}% of reviews ({t.mentions})</div>
          </div>
        ))}
        {topics.length === 0 && <p className="text-muted text-sm">No reviews imported yet.</p>}
      </div>

      {mining.length > 0 && (
        <div className="mb-10">
          <h3 className="text-sm font-medium text-ink mb-3">Review mining — recurring themes</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {mining.map((m) => (
              <div key={m.phrase} className="bg-bronze/8 border border-bronze/25 rounded-2xl px-5 py-4">
                <div className="text-sm capitalize text-charcoal">"{m.phrase}"</div>
                <div className="text-xs text-muted mt-1">Mentioned in {m.share_of_reviews}% of reviews ({m.mentions} mentions) — a candidate for marketing content.</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <h3 className="text-sm font-medium text-ink mb-3">Recent reviews</h3>
      <div className="space-y-3">
        {reviews.map((r) => (
          <div key={r.id} className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
            <div className="flex items-center justify-between text-xs text-muted mb-1.5">
              <span>{r.source} · {formatDate(r.review_date)} · {r.guest_country}</span>
              {r.rating && <span className="text-bronze">★ {r.rating}</span>}
            </div>
            <p className="text-sm text-charcoal">{r.raw_text}</p>
          </div>
        ))}
        {reviews.length === 0 && <p className="text-muted text-sm">No reviews imported yet.</p>}
      </div>
    </div>
  );
}
