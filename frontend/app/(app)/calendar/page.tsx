"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";
import { useCurrency, formatMoney } from "@/lib/currency";
import { formatDate } from "@/lib/format";

type ViewMode = "month" | "quarter" | "year";

interface Day {
  date: string;
  is_booked: boolean;
  adr: number | null;
  guest_country: string | null;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_LABEL = (d: Date) => d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
const SHORT_MONTH_LABEL = (d: Date) => d.toLocaleDateString("en-US", { month: "short", year: "numeric" });

function monthBounds(base: Date, offset: number) {
  const d = new Date(base.getFullYear(), base.getMonth() + offset, 1);
  const start = new Date(d.getFullYear(), d.getMonth(), 1);
  const end = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  return { start, end };
}
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Demand is derived from real nearby-occupancy density (how full the
 * surrounding ±5 days already are) — never a fabricated forecast. Framed to
 * the viewer as "based on nearby occupancy" rather than a price-elasticity
 * prediction, which this product deliberately does not claim to have yet
 * (see docs/ARCHITECTURE.md section 5/10). */
function nearbyDemand(days: Day[], index: number): "High" | "Moderate" | "Low" {
  const window = days.slice(Math.max(0, index - 5), index).concat(days.slice(index + 1, index + 6));
  if (window.length === 0) return "Moderate";
  const bookedShare = window.filter((d) => d.is_booked).length / window.length;
  if (bookedShare >= 0.7) return "High";
  if (bookedShare < 0.4) return "Low";
  return "Moderate";
}

function MonthGrid({ month, days, currency, targetAdr }: { month: Date; days: Day[]; currency: string; targetAdr: number | null }) {
  const leadingBlanks = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
  return (
    <div>
      <div className="grid grid-cols-7 gap-1.5 text-center text-[10px] text-muted uppercase mb-1.5">
        {WEEKDAYS.map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1.5">
        {Array.from({ length: leadingBlanks }).map((_, i) => (
          <div key={`b${i}`} />
        ))}
        {days.map((day, i) => {
          const demand = !day.is_booked ? nearbyDemand(days, i) : null;
          const d = new Date(day.date);
          return (
            <div
              key={day.date}
              className={`cal-cell aspect-square text-[10.5px] ${
                day.is_booked
                  ? "bg-bronze/12 border border-bronze/35"
                  : demand === "High"
                  ? "bg-clay/12 border border-clay/35"
                  : "bg-taupe/40 border border-taupedark/40"
              }`}
              title={
                day.is_booked
                  ? `${formatDate(day.date)} · Booked · ${formatMoney(day.adr, currency)}${day.guest_country ? " · " + day.guest_country : ""}`
                  : `${formatDate(day.date)} · Available · Target ${formatMoney(targetAdr, currency)} · ${demand} nearby demand`
              }
            >
              <span className="text-charcoal font-medium">{d.getDate()}</span>
              {day.is_booked ? (
                <span className="text-bronzedark leading-tight">{formatMoney(day.adr, currency)}</span>
              ) : (
                <span className={`leading-tight ${demand === "High" ? "text-clay" : "text-muted"}`}>
                  {demand === "High" ? "High demand" : "Open"}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MiniMonth({ month, days }: { month: Date; days: Day[] }) {
  const leadingBlanks = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
  return (
    <div>
      <div className="text-xs text-muted mb-2">{SHORT_MONTH_LABEL(month)}</div>
      <div className="grid grid-cols-7 gap-[3px]">
        {Array.from({ length: leadingBlanks }).map((_, i) => (
          <div key={`b${i}`} className="w-full aspect-square" />
        ))}
        {days.map((day, i) => {
          const demand = !day.is_booked ? nearbyDemand(days, i) : null;
          return (
            <div
              key={day.date}
              title={`${formatDate(day.date)} · ${day.is_booked ? "Booked" : "Available · " + demand + " nearby demand"}`}
              className={`w-full aspect-square rounded-[3px] ${
                day.is_booked ? "bg-bronze/70" : demand === "High" ? "bg-clay/50" : "bg-taupe"
              }`}
            />
          );
        })}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const { displayCurrency, withCurrency } = useCurrency();
  const [view, setView] = useState<ViewMode>("month");
  const [monthOffset, setMonthOffset] = useState(0);
  const [days, setDays] = useState<Day[]>([]);
  const [targetAdr, setTargetAdr] = useState<number | null>(null);

  const spanMonths = view === "month" ? 1 : view === "quarter" ? 3 : 12;

  const rangeStart = useMemo(() => new Date(new Date().getFullYear(), new Date().getMonth() + monthOffset, 1), [monthOffset]);
  const rangeEnd = useMemo(() => new Date(rangeStart.getFullYear(), rangeStart.getMonth() + spanMonths, 1), [rangeStart, spanMonths]);

  useEffect(() => {
    apiGet(withCurrency(`/api/reservations/calendar?start=${iso(rangeStart)}&end=${iso(rangeEnd)}`)).then(setDays);
    apiGet<any>(withCurrency("/api/dashboard/today")).then((t) => setTargetAdr(t.target_adr));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeStart.getTime(), rangeEnd.getTime(), displayCurrency]);

  const monthsInView = Array.from({ length: spanMonths }, (_, i) => new Date(rangeStart.getFullYear(), rangeStart.getMonth() + i, 1));

  function daysForMonth(m: Date): Day[] {
    const startIso = iso(m);
    const endIso = iso(new Date(m.getFullYear(), m.getMonth() + 1, 1));
    return days.filter((d) => d.date >= startIso && d.date < endIso);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-serif text-3xl text-ink">Calendar</h1>
        <div className="flex gap-1 bg-taupe/60 rounded-full p-1">
          {(["month", "quarter", "year"] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`text-xs px-3.5 py-1.5 rounded-full capitalize ${view === v ? "bg-warmwhite shadow-card text-ink" : "text-muted"}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-5 md:p-7 mb-8">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => setMonthOffset((o) => o - spanMonths)} className="text-xs px-2.5 py-1.5 rounded-full hover:bg-taupe">
            ← Prev
          </button>
          <h3 className="font-serif text-lg text-ink">
            {view === "month" ? MONTH_LABEL(rangeStart) : `${SHORT_MONTH_LABEL(monthsInView[0])} – ${SHORT_MONTH_LABEL(monthsInView[monthsInView.length - 1])}`}
          </h3>
          <button onClick={() => setMonthOffset((o) => o + spanMonths)} className="text-xs px-2.5 py-1.5 rounded-full hover:bg-taupe">
            Next →
          </button>
        </div>

        {view === "month" ? (
          <MonthGrid month={rangeStart} days={daysForMonth(rangeStart)} currency={displayCurrency} targetAdr={targetAdr} />
        ) : (
          <div className={`grid gap-6 ${view === "quarter" ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"}`}>
            {monthsInView.map((m) => (
              <MiniMonth key={m.toISOString()} month={m} days={daysForMonth(m)} />
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-5 mt-7 pt-5 border-t border-taupedark/40 text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-bronze/70 inline-block" /> Booked
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-clay/50 inline-block" /> Available · high nearby demand
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-taupe border border-taupedark/50 inline-block" /> Available
          </span>
        </div>
      </div>

      <p className="text-xs text-muted max-w-2xl">
        "Nearby demand" reflects how booked the surrounding week already is — a real, derived signal, not a price
        forecast. Full price-elasticity forecasting is on the roadmap (see Forecast).
      </p>
    </div>
  );
}
