"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import ActionCard from "@/components/ActionCard";

const CATEGORIES = ["all", "pricing", "marketing", "experience", "operations"];

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<any[]>([]);
  const [category, setCategory] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  function load() {
    apiGet("/api/recommendations?status=open").then(setRecs);
  }
  useEffect(load, []);

  async function refresh() {
    setRefreshing(true);
    try {
      await apiPost("/api/recommendations/refresh");
      load();
    } finally {
      setRefreshing(false);
    }
  }

  async function dismiss(id: number) {
    await apiPost(`/api/recommendations/${id}/dismiss`);
    load();
  }
  async function markActioned(id: number) {
    await apiPost(`/api/recommendations/${id}/action`);
    load();
  }

  const filtered = category === "all" ? recs : recs.filter((r) => r.category === category);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-3xl">Recommendations</h1>
        <button onClick={refresh} disabled={refreshing} className="text-xs px-3 py-1.5 rounded-md border border-taupedark hover:bg-taupe disabled:opacity-60">
          {refreshing ? "Refreshing…" : "Refresh recommendations"}
        </button>
      </div>

      <div className="flex gap-1 bg-taupe/60 rounded-md p-1 mb-6 w-fit">
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => setCategory(c)} className={`text-xs px-3 py-1.5 rounded-md capitalize ${category === c ? "bg-warmwhite shadow-card" : "text-muted"}`}>
            {c}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-8 text-center text-muted text-sm">
          No open recommendations in this category.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((r) => (
            <ActionCard key={r.id} rec={r} onDismiss={() => dismiss(r.id)} onAction={() => markActioned(r.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
