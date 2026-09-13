"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, PieChart, Pie, Cell,
} from "recharts";
import { apiGet } from "@/lib/api";
import { formatPct } from "@/lib/format";
import { useCurrency, formatMoney } from "@/lib/currency";
import { useDateRange } from "@/lib/dateRange";
import StatCard from "@/components/StatCard";

const PIE_COLORS = ["#A3814F", "#74805F", "#6C8299", "#BE8657"];

export default function RevenuePage() {
  const { displayCurrency, rateMode, withCurrency } = useCurrency();
  const { start, end, label } = useDateRange();
  const [summary, setSummary] = useState<any>(null);
  const [channelMix, setChannelMix] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [leadTime, setLeadTime] = useState<any>(null);
  const [los, setLos] = useState<any>(null);
  const [cancellations, setCancellations] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      apiGet(withCurrency(`/api/analytics/summary?start=${start}&end=${end}`)),
      apiGet(withCurrency(`/api/analytics/channel-mix?start=${start}&end=${end}`)),
      apiGet(`/api/analytics/lead-time?start=${start}&end=${end}`),
      apiGet(`/api/analytics/length-of-stay?start=${start}&end=${end}`),
      apiGet(`/api/analytics/cancellations?start=${start}&end=${end}`),
      apiGet(withCurrency("/api/analytics/monthly-trend?months=12")),
    ]).then(([s, cm, lt, l, c, t]) => {
      setSummary(s);
      setChannelMix(cm);
      setLeadTime(lt);
      setLos(l);
      setCancellations(c);
      setTrend(t);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end, displayCurrency, rateMode]);

  if (!summary) return <p className="text-muted text-sm">Loading…</p>;
  const cur = summary.current;
  const prev = summary.previous_period;
  const yoy = summary.same_period_last_year;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-3xl text-ink">Revenue</h1>
        <span className="text-xs text-muted">Last {label.toLowerCase()}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard label="Occupancy" value={formatPct(cur.occupancy_pct)} sublabel={prev ? `${(cur.occupancy_pct - prev.occupancy_pct).toFixed(1)} pts vs prior period` : undefined} />
        <StatCard label="ADR" value={formatMoney(cur.adr, displayCurrency)} sublabel={yoy?.adr ? `${formatMoney(yoy.adr, displayCurrency)} same period last year` : undefined} />
        <StatCard label="RevPAR" value={formatMoney(cur.revpar, displayCurrency)} />
        <StatCard label="Gross revenue" value={formatMoney(cur.gross_revenue, displayCurrency)} sublabel={`Net: ${formatMoney(cur.net_revenue, displayCurrency)}`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Avg length of stay" value={los?.mean_nights ? `${los.mean_nights} nights` : "—"} />
        <StatCard label="Avg lead time" value={leadTime?.mean_days ? `${leadTime.mean_days} days` : "—"} />
        <StatCard label="Cancellation rate" value={formatPct(cancellations?.rate_pct)} />
        <StatCard label="Reservations" value={String(cur.reservation_count)} />
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-10">
        <div className="md:col-span-2 bg-warmwhite border border-taupedark/50 rounded-2xl p-6">
          <h3 className="text-sm font-medium mb-5 text-ink">Occupancy & ADR — last 12 months</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="0" vertical={false} stroke="#EFE8D9" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8C8271" }} axisLine={{ stroke: "#DDD2BC" }} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#8C8271" }} axisLine={false} tickLine={false} width={36} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#8C8271" }} axisLine={false} tickLine={false} width={36} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #DDD2BC" }} />
              <Line yAxisId="left" type="monotone" dataKey="occupancy_pct" name="Occupancy %" stroke="#A3814F" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="adr" name="ADR" stroke="#6C8299" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6">
          <h3 className="text-sm font-medium mb-5 text-ink">Channel mix (by revenue)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={channelMix} dataKey="gross_revenue" nameKey="channel" innerRadius={48} outerRadius={78} paddingAngle={2} stroke="none">
                {channelMix.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => formatMoney(v, displayCurrency)} contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #DDD2BC" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-3">
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

      <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 mb-10">
        <h3 className="text-sm font-medium mb-5 text-ink">Monthly revenue</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trend}>
            <CartesianGrid strokeDasharray="0" vertical={false} stroke="#EFE8D9" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8C8271" }} axisLine={{ stroke: "#DDD2BC" }} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#8C8271" }} axisLine={false} tickLine={false} width={48} />
            <Tooltip formatter={(v: number) => formatMoney(v, displayCurrency)} contentStyle={{ fontSize: 12, borderRadius: 10, border: "1px solid #DDD2BC" }} />
            <Bar dataKey="gross_revenue" name="Gross revenue" fill="#A3814F" radius={[4, 4, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
