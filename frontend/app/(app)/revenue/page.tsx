"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, PieChart, Pie, Cell,
} from "recharts";
import { apiGet } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";
import StatCard from "@/components/StatCard";

const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "12 months", days: 365 },
];

const PIE_COLORS = ["#A47B4E", "#6E7A64", "#B5654A", "#8A8378"];

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function RevenuePage() {
  const [rangeDays, setRangeDays] = useState(30);
  const [summary, setSummary] = useState<any>(null);
  const [channelMix, setChannelMix] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [leadTime, setLeadTime] = useState<any>(null);
  const [los, setLos] = useState<any>(null);
  const [cancellations, setCancellations] = useState<any>(null);

  useEffect(() => {
    const start = isoDaysAgo(rangeDays);
    const end = todayIso();
    Promise.all([
      apiGet(`/api/analytics/summary?start=${start}&end=${end}`),
      apiGet(`/api/analytics/channel-mix?start=${start}&end=${end}`),
      apiGet(`/api/analytics/lead-time?start=${start}&end=${end}`),
      apiGet(`/api/analytics/length-of-stay?start=${start}&end=${end}`),
      apiGet(`/api/analytics/cancellations?start=${start}&end=${end}`),
      apiGet(`/api/analytics/monthly-trend?months=12`),
    ]).then(([s, cm, lt, l, c, t]) => {
      setSummary(s);
      setChannelMix(cm);
      setLeadTime(lt);
      setLos(l);
      setCancellations(c);
      setTrend(t);
    });
  }, [rangeDays]);

  if (!summary) return <p className="text-muted text-sm">Loading…</p>;
  const cur = summary.current;
  const prev = summary.previous_period;
  const yoy = summary.same_period_last_year;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-3xl">Revenue</h1>
        <div className="flex gap-1 bg-taupe/60 rounded-md p-1">
          {RANGE_OPTIONS.map((r) => (
            <button
              key={r.days}
              onClick={() => setRangeDays(r.days)}
              className={`text-xs px-3 py-1.5 rounded-md ${rangeDays === r.days ? "bg-warmwhite shadow-card" : "text-muted"}`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard label="Occupancy" value={formatPct(cur.occupancy_pct)} sublabel={prev ? `${(cur.occupancy_pct - prev.occupancy_pct).toFixed(1)} pts vs prior period` : undefined} />
        <StatCard label="ADR" value={formatCurrency(cur.adr)} sublabel={yoy?.adr ? `${formatCurrency(yoy.adr)} same period last year` : undefined} />
        <StatCard label="RevPAR" value={formatCurrency(cur.revpar)} />
        <StatCard label="Gross revenue" value={formatCurrency(cur.gross_revenue)} sublabel={`Net: ${formatCurrency(cur.net_revenue)}`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Avg length of stay" value={los?.mean_nights ? `${los.mean_nights} nights` : "—"} />
        <StatCard label="Avg lead time" value={leadTime?.mean_days ? `${leadTime.mean_days} days` : "—"} />
        <StatCard label="Cancellation rate" value={formatPct(cancellations?.rate_pct)} />
        <StatCard label="Reservations" value={String(cur.reservation_count)} />
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-10">
        <div className="md:col-span-2 bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium mb-4">Occupancy & ADR — last 12 months</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EFE9E1" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8A8378" }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#8A8378" }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#8A8378" }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #DCD3C6" }} />
              <Line yAxisId="left" type="monotone" dataKey="occupancy_pct" name="Occupancy %" stroke="#A47B4E" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="adr" name="ADR" stroke="#6E7A64" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card">
          <h3 className="text-sm font-medium mb-4">Channel mix (by revenue)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={channelMix} dataKey="gross_revenue" nameKey="channel" innerRadius={45} outerRadius={80} paddingAngle={2}>
                {channelMix.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #DCD3C6" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {channelMix.map((c, i) => (
              <div key={c.channel} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                  {c.channel}
                </span>
                <span className="text-muted">{c.revenue_share_pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card mb-10">
        <h3 className="text-sm font-medium mb-4">Monthly revenue</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EFE9E1" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8A8378" }} />
            <YAxis tick={{ fontSize: 11, fill: "#8A8378" }} />
            <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #DCD3C6" }} />
            <Bar dataKey="gross_revenue" name="Gross revenue" fill="#A47B4E" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
