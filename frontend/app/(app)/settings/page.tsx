"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPut } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function SettingsPage() {
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
      <h1 className="font-serif text-3xl mb-8">Settings</h1>

      <h3 className="text-sm font-medium mb-3">Property</h3>
      <form onSubmit={save} className="bg-warmwhite border border-taupedark/50 rounded-lg p-6 shadow-card space-y-4 max-w-lg mb-10">
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Property name</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border border-taupedark rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Address</label>
          <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="w-full border border-taupedark rounded-md px-3 py-2 text-sm" />
        </div>
        <div className="flex gap-4">
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Bedrooms</label>
            <input type="number" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })} className="w-24 border border-taupedark rounded-md px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Currency</label>
            <input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="w-24 border border-taupedark rounded-md px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex gap-4">
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Target occupancy %</label>
            <input type="number" value={form.target_occupancy_pct} onChange={(e) => setForm({ ...form, target_occupancy_pct: e.target.value })} className="w-32 border border-taupedark rounded-md px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Target ADR</label>
            <input type="number" value={form.target_adr} onChange={(e) => setForm({ ...form, target_adr: e.target.value })} className="w-32 border border-taupedark rounded-md px-3 py-2 text-sm" />
          </div>
        </div>
        <button className="text-xs px-4 py-2 rounded-md bg-charcoal text-warmwhite hover:bg-bronzedark">Save changes</button>
        {saved && <span className="text-xs text-sage ml-3">Saved.</span>}
      </form>

      {property?.is_demo && (
        <div className="bg-bronze/10 border border-bronze/30 rounded-lg p-5 mb-10 max-w-lg text-sm">
          This property currently shows <strong>DEMO DATA</strong>. Import your own bookings, reviews and competitor
          rates from the Bookings, Guest Experience and Competitors pages — new imports are added alongside the
          demo data, so once you're ready for production use, start a fresh account.
        </div>
      )}

      <h3 className="text-sm font-medium mb-3">Import history</h3>
      <div className="overflow-x-auto border border-taupedark/40 rounded-lg max-w-2xl">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50">
            <tr>
              {["File", "Source", "Rows", "Status", "Uploaded"].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.map((b) => (
              <tr key={b.id} className="border-t border-taupedark/30">
                <td className="px-3 py-2">{b.filename}</td>
                <td className="px-3 py-2">{b.source_type}</td>
                <td className="px-3 py-2">{b.row_count}</td>
                <td className="px-3 py-2 capitalize">{b.status}</td>
                <td className="px-3 py-2">{formatDate(b.uploaded_at)}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr><td colSpan={5} className="px-3 py-4 text-center text-muted">No imports yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
