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
      <h1 className="font-serif text-3xl mb-1">Competitors</h1>
      <p className="text-muted text-sm mb-8">
        Manually entered or CSV-imported comparable villas — never scraped. Rate observations power the pricing
        recommendations on the Today and Recommendations pages.
      </p>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <form onSubmit={addCompetitor} className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card space-y-3">
          <h3 className="text-sm font-medium mb-1">Add a competitor</h3>
          <input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border border-taupedark rounded-md px-3 py-2 text-sm"
          />
          <div className="flex gap-3">
            <input
              type="number"
              placeholder="Bedrooms"
              value={form.bedrooms}
              onChange={(e) => setForm({ ...form, bedrooms: Number(e.target.value) })}
              className="w-28 border border-taupedark rounded-md px-3 py-2 text-sm"
            />
            <input
              placeholder="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="flex-1 border border-taupedark rounded-md px-3 py-2 text-sm"
            />
          </div>
          <button className="text-xs px-4 py-2 rounded-md bg-charcoal text-warmwhite hover:bg-bronzedark">Add competitor</button>
        </form>

        <ImportWizard onImported={load} />
      </div>

      <div className="overflow-x-auto border border-taupedark/40 rounded-lg">
        <table className="text-sm w-full">
          <thead className="bg-taupe/50">
            <tr>
              {["Name", "Bedrooms", "Location", "Pool", "Sauna", "Review score", "Reviews"].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c) => (
              <tr key={c.id} className="border-t border-taupedark/30">
                <td className="px-3 py-2">{c.name}</td>
                <td className="px-3 py-2">{c.bedrooms}</td>
                <td className="px-3 py-2">{c.location}</td>
                <td className="px-3 py-2">{c.has_pool ? "Yes" : "No"}</td>
                <td className="px-3 py-2">{c.has_sauna ? "Yes" : "No"}</td>
                <td className="px-3 py-2">{c.review_score ?? "—"}</td>
                <td className="px-3 py-2">{c.review_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
