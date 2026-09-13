"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { formatCurrency, formatPct, formatDate } from "@/lib/format";
import StatCard from "@/components/StatCard";
import ActionCard from "@/components/ActionCard";
import DemoBanner from "@/components/DemoBanner";

interface Today {
  property_name: string;
  target_occupancy_pct: number;
  target_adr: number;
  currency: string;
  current_occupancy_today_pct: number;
  next_30_days_occupancy_pct: number;
  next_30_days_revenue: number;
  current_adr_trailing: number;
  upcoming_empty_nights_30d: number;
  next_arrival: { date: string; guest_country: string | null; nights: number } | null;
  next_departure: { date: string } | null;
  recent_bookings_count_7d: number;
  recent_cancellations_count_14d: number;
  actions: any[];
}

interface PropertyInfo {
  is_demo: boolean;
}

export default function TodayPage() {
  const [data, setData] = useState<Today | null>(null);
  const [property, setProperty] = useState<PropertyInfo | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [today, prop] = await Promise.all([apiGet<Today>("/api/dashboard/today"), apiGet<PropertyInfo>("/api/property")]);
      setData(today);
      setProperty(prop);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

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
  if (!data) return <p className="text-muted text-sm">Loading…</p>;

  return (
    <div>
      <DemoBanner show={!!property?.is_demo} />

      <div className="flex items-baseline justify-between mb-1">
        <h1 className="font-serif text-3xl">Good day.</h1>
        <span className="text-xs text-muted">{data.property_name}</span>
      </div>
      <p className="text-muted text-sm mb-8">Here is what's happening at the villa, and what to do about it.</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard label="Occupancy today" value={formatPct(data.current_occupancy_today_pct)} />
        <StatCard
          label="Next 30 days occupancy"
          value={formatPct(data.next_30_days_occupancy_pct)}
          sublabel={`Target ${formatPct(data.target_occupancy_pct)}`}
          accent={data.next_30_days_occupancy_pct >= data.target_occupancy_pct ? "sage" : "terracotta"}
        />
        <StatCard label="Trailing ADR" value={formatCurrency(data.current_adr_trailing, data.currency)} sublabel={`Target ${formatCurrency(data.target_adr, data.currency)}`} />
        <StatCard label="Next 30 days revenue on books" value={formatCurrency(data.next_30_days_revenue, data.currency)} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Next arrival" value={data.next_arrival ? formatDate(data.next_arrival.date) : "None scheduled"} sublabel={data.next_arrival ? `${data.next_arrival.nights} nights · ${data.next_arrival.guest_country || "—"}` : undefined} />
        <StatCard label="Next departure" value={data.next_departure ? formatDate(data.next_departure.date) : "None scheduled"} />
        <StatCard label="Empty nights, next 30d" value={String(data.upcoming_empty_nights_30d)} accent={data.upcoming_empty_nights_30d > 10 ? "terracotta" : "sage"} />
        <StatCard label="Bookings (7d) / Cancellations (14d)" value={`${data.recent_bookings_count_7d} / ${data.recent_cancellations_count_14d}`} />
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-xl">What should I do today?</h2>
        <button
          onClick={refreshRecommendations}
          disabled={refreshing}
          className="text-xs px-3 py-1.5 rounded-md border border-taupedark hover:bg-taupe disabled:opacity-60"
        >
          {refreshing ? "Refreshing…" : "Refresh recommendations"}
        </button>
      </div>

      {data.actions.length === 0 ? (
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-8 text-center text-muted text-sm">
          No open recommendations. Click "Refresh recommendations" to analyse the latest data, or import bookings and
          reviews from Settings first.
        </div>
      ) : (
        <div className="space-y-4">
          {data.actions.map((a) => (
            <ActionCard key={a.id} rec={a} />
          ))}
        </div>
      )}
    </div>
  );
}
