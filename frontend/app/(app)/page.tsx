"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useCurrency, formatMoney } from "@/lib/currency";
import { useDateRange } from "@/lib/dateRange";
import { Stat } from "@/components/StatCard";
import ActionCard from "@/components/ActionCard";
import DemoBanner from "@/components/DemoBanner";
import PropertyHero from "@/components/PropertyHero";

interface Today {
  property_name: string;
  target_occupancy_pct: number;
  upcoming_empty_nights_30d: number;
  next_arrival: { date: string; guest_country: string | null; nights: number } | null;
  next_departure: { date: string } | null;
  actions: any[];
}

interface PropertyInfo {
  is_demo: boolean;
  address: string;
}

function pctDelta(current: number | null, previous: number | null): { direction: "up" | "down" | "flat"; text: string } | null {
  if (current === null || previous === null) return null;
  const diff = current - previous;
  if (Math.abs(diff) < 0.05) return { direction: "flat", text: "flat vs previous period" };
  return { direction: diff > 0 ? "up" : "down", text: `${diff > 0 ? "+" : ""}${diff.toFixed(1)} pts vs previous period` };
}

function relDelta(current: number | null, previous: number | null): { direction: "up" | "down" | "flat"; text: string } | null {
  if (current === null || previous === null || previous === 0) return null;
  const pct = ((current - previous) / previous) * 100;
  if (Math.abs(pct) < 0.5) return { direction: "flat", text: "flat vs previous period" };
  return { direction: pct > 0 ? "up" : "down", text: `${pct > 0 ? "+" : ""}${pct.toFixed(1)}% vs previous period` };
}

export default function OverviewPage() {
  const { displayCurrency, rateMode, withCurrency } = useCurrency();
  const { start, end, label } = useDateRange();
  const [today, setToday] = useState<Today | null>(null);
  const [property, setProperty] = useState<PropertyInfo | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [t, prop, s] = await Promise.all([
        apiGet<Today>(withCurrency("/api/dashboard/today")),
        apiGet<PropertyInfo>("/api/property"),
        apiGet<any>(withCurrency(`/api/analytics/summary?start=${start}&end=${end}`)),
      ]);
      setToday(t);
      setProperty(prop);
      setSummary(s);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end, displayCurrency, rateMode]);

  async function refreshRecommendations() {
    setRefreshing(true);
    try {
      await apiPost("/api/recommendations/refresh");
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  if (error) return <p className="text-terracotta text-sm">{error}</p>;
  if (!today || !summary) return <p className="text-muted text-sm">Loading…</p>;

  const cur = summary.current;
  const prev = summary.previous_period;

  return (
    <div>
      <DemoBanner show={!!property?.is_demo} />

      <PropertyHero name={today.property_name} address={property?.address || ""} />

      <div className="flex items-baseline justify-between mb-6">
        <h2 className="font-serif text-xl text-ink">Performance overview</h2>
        <span className="text-xs text-muted">Last {label.toLowerCase()} vs previous period</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-8 mb-10 pb-10 border-b border-taupedark/50">
        <Stat
          label="Occupancy"
          value={`${cur.occupancy_pct}%`}
          deltaLabel={pctDelta(cur.occupancy_pct, prev?.occupancy_pct ?? null)?.text}
          deltaDirection={pctDelta(cur.occupancy_pct, prev?.occupancy_pct ?? null)?.direction}
        />
        <Stat
          label="ADR"
          value={formatMoney(cur.adr, displayCurrency)}
          deltaLabel={relDelta(cur.adr, prev?.adr ?? null)?.text}
          deltaDirection={relDelta(cur.adr, prev?.adr ?? null)?.direction}
        />
        <Stat
          label="Revenue"
          value={formatMoney(cur.gross_revenue, displayCurrency)}
          deltaLabel={relDelta(cur.gross_revenue, prev?.gross_revenue ?? null)?.text}
          deltaDirection={relDelta(cur.gross_revenue, prev?.gross_revenue ?? null)?.direction}
        />
        <Stat
          label="RevPAR"
          value={formatMoney(cur.revpar, displayCurrency)}
          deltaLabel={relDelta(cur.revpar, prev?.revpar ?? null)?.text}
          deltaDirection={relDelta(cur.revpar, prev?.revpar ?? null)?.direction}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-xs text-muted mb-10">
        <span>
          <span className="text-charcoal">Next arrival</span>{" "}
          {today.next_arrival ? `${formatDate(today.next_arrival.date)} · ${today.next_arrival.nights}n · ${today.next_arrival.guest_country || "—"}` : "None scheduled"}
        </span>
        <span>
          <span className="text-charcoal">Next departure</span> {today.next_departure ? formatDate(today.next_departure.date) : "None scheduled"}
        </span>
        <span>
          <span className="text-charcoal">Empty nights, next 30d</span>{" "}
          <span className={today.upcoming_empty_nights_30d > 10 ? "text-terracotta" : "text-sage"}>{today.upcoming_empty_nights_30d}</span>
        </span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-xl text-ink">Today's Intelligence</h2>
        <button
          onClick={refreshRecommendations}
          disabled={refreshing}
          className="text-xs px-3.5 py-1.5 rounded-full border border-taupedark hover:bg-taupe disabled:opacity-60"
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {today.actions.length === 0 ? (
        <div className="bg-warmwhite border border-taupedark/50 rounded-xl px-5 py-10 text-center text-muted text-sm">
          No open recommendations. Click "Refresh" to analyse the latest data, or import bookings and reviews from
          Settings first.
        </div>
      ) : (
        <div className="space-y-3.5">
          {today.actions.map((a) => (
            <ActionCard key={a.id} rec={a} />
          ))}
        </div>
      )}
    </div>
  );
}
