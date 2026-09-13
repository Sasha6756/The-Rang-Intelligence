"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatDate } from "@/lib/format";

const WINDOWS = [
  { label: "Next 2 weeks", startDays: 0, nights: 14 },
  { label: "Weeks 3–6", startDays: 14, nights: 28 },
  { label: "Months 2–3", startDays: 42, nights: 60 },
];

function addDays(base: Date, days: number) {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d;
}
const iso = (d: Date) => d.toISOString().slice(0, 10);

const LABEL_META: Record<string, { text: string; color: string }> = {
  faster: { text: "Booking faster than usual", color: "text-sage" },
  slower: { text: "Booking slower than usual", color: "text-terracotta" },
  normal: { text: "Tracking normally", color: "text-charcoal" },
  insufficient_data: { text: "Not enough history yet", color: "text-muted" },
};

export default function ForecastPage() {
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    const today = new Date();
    Promise.all(
      WINDOWS.map((w) => {
        const start = addDays(today, w.startDays);
        const end = addDays(start, w.nights);
        return apiGet(`/api/analytics/booking-pace?window_start=${iso(start)}&window_end=${iso(end)}`).then((r) => ({
          ...w, start: iso(start), end: iso(end), pace: r,
        }));
      })
    ).then(setRows);
  }, []);

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-1">Forecast</h1>
      <p className="text-muted text-sm mb-8 max-w-2xl">
        Full occupancy and revenue forecasting (trend + seasonal modelling with confidence intervals) is on the
        roadmap. What's already real and working: booking-pace comparisons — how fully an upcoming window is booked
        right now versus how fully comparable windows were booked at the same point in previous years.
      </p>

      <div className="space-y-4 mb-10">
        {rows.map((r) => {
          const meta = LABEL_META[r.pace?.label] || LABEL_META.insufficient_data;
          return (
            <div key={r.label} className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 flex items-center justify-between flex-wrap gap-4">
              <div>
                <div className="font-serif text-lg text-ink">{r.label}</div>
                <div className="text-xs text-muted mt-0.5">
                  {formatDate(r.start)} – {formatDate(r.end)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-serif tnum text-ink">
                  {r.pace?.current_pct ?? "—"}%{" "}
                  <span className="text-sm text-muted font-sans">booked so far</span>
                </div>
                <div className={`text-xs mt-1 ${meta.color}`}>
                  {meta.text}
                  {r.pace?.historical_pct != null && ` · historical average ${r.pace.historical_pct}% at this lead time`}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-taupe/40 border border-taupedark/40 rounded-2xl p-6 text-sm text-muted max-w-2xl">
        <span className="text-charcoal font-medium">Coming in a later phase:</span> trend + seasonal-baseline
        occupancy and revenue forecasts with confidence intervals, and a scenario planner ("what if I drop price
        10% for this window"). See the architecture document's roadmap for the full plan — nothing here is
        simulated ahead of being built.
      </div>
    </div>
  );
}
