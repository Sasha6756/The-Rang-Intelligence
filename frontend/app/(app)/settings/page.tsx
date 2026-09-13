"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPut } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { CURRENCIES, useCurrency } from "@/lib/currency";

export default function SettingsPage() {
  const { displayCurrency, setDisplayCurrency, rates, refreshRates, refreshing } = useCurrency();
  const [property, setProperty] = useState<any>(null);
  const [form, setForm] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/api/property").then((p) => {
      setProperty(p);
      setForm(p);
    });
    apiGet("/api/imports/history").then(setHistory);
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const updated = await apiPut("/api/property", {
      name: form.name,
      address: form.address,
      bedrooms: Number(form.bedrooms),
      currency: form.currency,
      target_occupancy_pct: Number(form.target_occupancy_pct),
      target_adr: Number(form.target_adr),
    });
    setProperty(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!form) return <p className="text-muted text-sm">Loading…</p>;

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-8">Settings</h1>

      <h3 className="text-sm font-medium text-ink mb-3">Property</h3>
      <form onSubmit={save} className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 space-y-4 max-w-lg mb-10">
        <div>
          <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Property name</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border border-taupedark rounded-lg px-3 py-2 text-sm bg-white" />
        </div>
        <div>
          <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Address</label>
          <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="w-full border border-taupedark rounded-lg px-3 py-2 text-sm bg-white" />
        </div>
        <div className="flex gap-4">
          <div>
            <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Bedrooms</label>
            <input type="number" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })} className="w-24 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white" />
          </div>
          <div>
            <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Base currency</label>
            <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="w-32 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white">
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>{c.code}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex gap-4">
          <div>
            <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Target occupancy %</label>
            <input type="number" value={form.target_occupancy_pct} onChange={(e) => setForm({ ...form, target_occupancy_pct: e.target.value })} className="w-32 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white" />
          </div>
          <div>
            <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Target ADR ({form.currency})</label>
            <input type="number" value={form.target_adr} onChange={(e) => setForm({ ...form, target_adr: e.target.value })} className="w-32 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white" />
          </div>
        </div>
        <button className="text-xs px-4 py-2 rounded-full bg-charcoal text-warmwhite hover:bg-ink">Save changes</button>
        {saved && <span className="text-xs text-sage ml-3">Saved.</span>}
      </form>

      <h3 className="text-sm font-medium text-ink mb-3">Currency</h3>
      <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 max-w-lg mb-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <label className="block text-[10.5px] uppercase tracking-wide text-muted mb-1">Default display currency</label>
            <select value={displayCurrency} onChange={(e) => setDisplayCurrency(e.target.value)} className="border border-taupedark rounded-lg px-3 py-2 text-sm bg-white">
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>{c.symbol} {c.code}</option>
              ))}
            </select>
          </div>
          <button
            onClick={refreshRates}
            disabled={refreshing}
            className="text-xs px-3.5 py-1.5 rounded-full border border-taupedark hover:bg-taupe disabled:opacity-60 h-fit"
          >
            {refreshing ? "Refreshing…" : "Refresh rates"}
          </button>
        </div>

        <div className="text-[10.5px] uppercase tracking-wide text-muted mb-2 mt-5">Exchange rates (base: {rates?.base_currency || "IDR"})</div>
        <div className="space-y-1.5">
          {rates?.currencies &&
            Object.entries(rates.currencies).map(([code, entry]: [string, any]) => (
              <div key={code} className="flex items-center justify-between text-sm border-t border-taupedark/30 py-2 first:border-t-0">
                <span className="text-charcoal">1 IDR = {entry.rate ? entry.rate.toFixed(8) : "—"} {code}</span>
                <span className={`text-xs ${entry.is_stale ? "text-clay" : "text-sage"}`}>
                  {entry.effective_date ? formatDate(entry.effective_date) : "no data yet"}
                  {entry.is_stale ? " · stale" : " · current"}
                </span>
              </div>
            ))}
        </div>
        <p className="text-[11px] text-muted mt-4 leading-relaxed">
          Rates refresh automatically once a day from {rates?.provider || "the exchange-rate provider"}. If a fetch
          ever fails, the last successful rate keeps being used and is clearly marked "stale" here rather than
          silently treated as current.
        </p>
      </div>

      {property?.is_demo && (
        <div className="bg-bronze/8 border border-bronze/25 rounded-2xl p-5 mb-10 max-w-lg text-sm text-charcoal">
          This property currently shows <strong>DEMO DATA</strong>. Import your own bookings, reviews and competitor
          rates from Bookings, Experience and Competitors — new imports are added alongside the demo data, so once
          you're ready for production use, start a fresh account.
        </div>
      )}

      <h3 className="text-sm font-medium text-ink mb-3">Import history</h3>
      <div className="overflow-x-auto bg-warmwhite border border-taupedark/50 rounded-2xl max-w-2xl">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50 text-[10.5px] uppercase tracking-wide text-muted">
            <tr>
              {["File", "Source", "Rows", "Status", "Uploaded"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.map((b) => (
              <tr key={b.id} className="border-t border-taupedark/30">
                <td className="px-4 py-3 text-charcoal">{b.filename}</td>
                <td className="px-4 py-3 text-muted">{b.source_type}</td>
                <td className="px-4 py-3 text-muted">{b.row_count}</td>
                <td className="px-4 py-3 text-muted capitalize">{b.status}</td>
                <td className="px-4 py-3 text-muted">{formatDate(b.uploaded_at)}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-muted">No imports yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
