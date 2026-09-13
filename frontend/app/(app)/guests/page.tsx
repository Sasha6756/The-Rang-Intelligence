"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatPct } from "@/lib/format";
import { useCurrency, formatMoney } from "@/lib/currency";

export default function GuestsPage() {
  const { displayCurrency, rateMode, withCurrency } = useCurrency();
  const [segments, setSegments] = useState<any[]>([]);
  const [countries, setCountries] = useState<any[]>([]);

  useEffect(() => {
    apiGet(withCurrency("/api/guests/segments")).then(setSegments);
    apiGet(withCurrency("/api/guests/country-mix")).then(setCountries);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCurrency, rateMode]);

  const priced = segments.filter((s) => s.avg_booking_value !== null);
  const mostValuable = [...priced].sort((a, b) => b.avg_booking_value - a.avg_booking_value)[0];
  const withLead = segments.filter((s) => s.avg_lead_time_days !== null);
  const easiestToConvert = [...withLead].sort((a, b) => a.avg_lead_time_days - b.avg_lead_time_days)[0];

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-1">Guests</h1>
      <p className="text-muted text-sm mb-8">Rule-based segmentation from your reservation history — auditable, not a black box.</p>

      {(mostValuable || easiestToConvert) && (
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          {mostValuable && (
            <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-5">
              <div className="text-[10.5px] uppercase tracking-wide text-bronze mb-1">Most valuable segment</div>
              <div className="font-serif text-lg text-ink">{mostValuable.segment}</div>
              <p className="text-sm text-muted mt-1">
                Average booking value {formatMoney(mostValuable.avg_booking_value, displayCurrency)}, {mostValuable.avg_length_of_stay} night average stay.
              </p>
            </div>
          )}
          {easiestToConvert && (
            <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-5">
              <div className="text-[10.5px] uppercase tracking-wide text-bronze mb-1">Easiest to convert directly</div>
              <div className="font-serif text-lg text-ink">{easiestToConvert.segment}</div>
              <p className="text-sm text-muted mt-1">Average lead time of just {easiestToConvert.avg_lead_time_days} days — worth targeting with direct campaigns.</p>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto bg-warmwhite border border-taupedark/50 rounded-2xl mb-10">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50 text-[10.5px] uppercase tracking-wide text-muted">
            <tr>
              {["Segment", "Reservations", "Avg stay", "Avg lead time", "Avg value", "Total revenue", "Cancellation rate"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {segments.map((s) => (
              <tr key={s.segment} className="border-t border-taupedark/30">
                <td className="px-4 py-3 text-charcoal">{s.segment}</td>
                <td className="px-4 py-3 text-muted">{s.reservation_count}</td>
                <td className="px-4 py-3 text-muted">{s.avg_length_of_stay ?? "—"} nights</td>
                <td className="px-4 py-3 text-muted">{s.avg_lead_time_days ?? "—"} days</td>
                <td className="px-4 py-3 text-charcoal tnum">{formatMoney(s.avg_booking_value, displayCurrency)}</td>
                <td className="px-4 py-3 text-charcoal tnum">{formatMoney(s.total_revenue, displayCurrency)}</td>
                <td className="px-4 py-3 text-muted">{formatPct(s.cancellation_rate_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-sm font-medium text-ink mb-3">Top guest countries</h3>
      <div className="overflow-x-auto bg-warmwhite border border-taupedark/50 rounded-2xl">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50 text-[10.5px] uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Country</th>
              <th className="px-4 py-3 text-left font-medium">Reservations</th>
              <th className="px-4 py-3 text-left font-medium">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {countries.map((c) => (
              <tr key={c.country} className="border-t border-taupedark/30">
                <td className="px-4 py-3 text-charcoal">{c.country}</td>
                <td className="px-4 py-3 text-muted">{c.reservations}</td>
                <td className="px-4 py-3 text-charcoal tnum">{formatMoney(c.revenue, displayCurrency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
