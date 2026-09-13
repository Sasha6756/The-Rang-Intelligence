"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";

export default function GuestsPage() {
  const [segments, setSegments] = useState<any[]>([]);
  const [countries, setCountries] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/api/guests/segments").then(setSegments);
    apiGet("/api/guests/country-mix").then(setCountries);
  }, []);

  const mostValuable = [...segments].sort((a, b) => b.avg_booking_value - a.avg_booking_value)[0];
  const easiestToConvert = [...segments].sort((a, b) => a.avg_lead_time_days - b.avg_lead_time_days)[0];

  return (
    <div>
      <h1 className="font-serif text-3xl mb-1">Guests</h1>
      <p className="text-muted text-sm mb-8">Rule-based segmentation from your reservation history — auditable, not a black box.</p>

      {segments.length > 0 && (
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card">
            <div className="text-[11px] uppercase tracking-wide text-bronze mb-1">Most valuable segment</div>
            <div className="font-serif text-lg">{mostValuable.segment}</div>
            <p className="text-sm text-muted mt-1">Average booking value {formatCurrency(mostValuable.avg_booking_value)}, {mostValuable.avg_length_of_stay} night average stay.</p>
          </div>
          <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card">
            <div className="text-[11px] uppercase tracking-wide text-bronze mb-1">Easiest to convert directly</div>
            <div className="font-serif text-lg">{easiestToConvert.segment}</div>
            <p className="text-sm text-muted mt-1">Average lead time of just {easiestToConvert.avg_lead_time_days} days — worth targeting with direct campaigns.</p>
          </div>
        </div>
      )}

      <div className="overflow-x-auto border border-taupedark/40 rounded-lg mb-10">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50">
            <tr>
              {["Segment", "Reservations", "Avg stay", "Avg lead time", "Avg value", "Total revenue", "Cancellation rate"].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {segments.map((s) => (
              <tr key={s.segment} className="border-t border-taupedark/30">
                <td className="px-3 py-2">{s.segment}</td>
                <td className="px-3 py-2">{s.reservation_count}</td>
                <td className="px-3 py-2">{s.avg_length_of_stay} nights</td>
                <td className="px-3 py-2">{s.avg_lead_time_days} days</td>
                <td className="px-3 py-2">{formatCurrency(s.avg_booking_value)}</td>
                <td className="px-3 py-2">{formatCurrency(s.total_revenue)}</td>
                <td className="px-3 py-2">{formatPct(s.cancellation_rate_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-sm font-medium mb-3">Top guest countries</h3>
      <div className="overflow-x-auto border border-taupedark/40 rounded-lg">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-xs">Country</th>
              <th className="px-3 py-2 text-left font-medium text-xs">Reservations</th>
              <th className="px-3 py-2 text-left font-medium text-xs">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {countries.map((c) => (
              <tr key={c.country} className="border-t border-taupedark/30">
                <td className="px-3 py-2">{c.country}</td>
                <td className="px-3 py-2">{c.reservations}</td>
                <td className="px-3 py-2">{formatCurrency(c.revenue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
