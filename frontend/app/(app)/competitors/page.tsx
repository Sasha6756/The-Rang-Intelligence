"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import ImportWizard from "@/components/ImportWizard";

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [form, setForm] = useState({ name: "", bedrooms: 5, location: "Uluwatu" });

  function load() {
    apiGet("/api/competitors").then(setCompetitors);
  }
  useEffect(load, []);

  async function addCompetitor(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name) return;
    await apiPost("/api/competitors", form);
    setForm({ name: "", bedrooms: 5, location: "Uluwatu" });
    load();
  }

  return (
    <div>
      <h1 className="font-serif text-3xl text-ink mb-1">Competitors</h1>
      <p className="text-muted text-sm mb-8">
        Manually entered or CSV-imported comparable villas — never scraped. Rate observations power the pricing
        recommendations on Overview and Insights.
      </p>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <form onSubmit={addCompetitor} className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 space-y-3">
          <h3 className="text-sm font-medium text-ink mb-1">Add a competitor</h3>
          <input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
          />
          <div className="flex gap-3">
            <input
              type="number"
              placeholder="Bedrooms"
              value={form.bedrooms}
              onChange={(e) => setForm({ ...form, bedrooms: Number(e.target.value) })}
              className="w-28 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
            />
            <input
              placeholder="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="flex-1 border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
            />
          </div>
          <button className="text-xs px-4 py-2 rounded-full bg-charcoal text-warmwhite hover:bg-ink">Add competitor</button>
        </form>

        <ImportWizard onImported={load} />
      </div>

      <div className="overflow-x-auto bg-warmwhite border border-taupedark/50 rounded-2xl">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50 text-[10.5px] uppercase tracking-wide text-muted">
            <tr>
              {["Name", "Bedrooms", "Location", "Pool", "Sauna", "Review score", "Reviews"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c) => (
              <tr key={c.id} className="border-t border-taupedark/30">
                <td className="px-4 py-3 text-charcoal">{c.name}</td>
                <td className="px-4 py-3 text-muted">{c.bedrooms}</td>
                <td className="px-4 py-3 text-muted">{c.location}</td>
                <td className="px-4 py-3 text-muted">{c.has_pool ? "Yes" : "No"}</td>
                <td className="px-4 py-3 text-muted">{c.has_sauna ? "Yes" : "No"}</td>
                <td className="px-4 py-3 text-charcoal">{c.review_score ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{c.review_count}</td>
              </tr>
            ))}
            {competitors.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">No competitors added yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
