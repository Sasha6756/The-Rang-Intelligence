"use client";

import { useEffect, useState } from "react";
import { apiGet, API_URL } from "@/lib/api";
import { formatCurrency, formatPct, formatDate } from "@/lib/format";

export default function ReportsPage() {
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    apiGet("/api/reports/weekly").then(setReport);
  }, []);

  function downloadMarkdown() {
    const token = localStorage.getItem("rang_token");
    fetch(`${API_URL}/api/reports/weekly.md`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.text())
      .then((text) => {
        const blob = new Blob([text], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "the-rang-weekly-intelligence.md";
        a.click();
        URL.revokeObjectURL(url);
      });
  }

  if (!report) return <p className="text-muted text-sm">Loading…</p>;
  const p = report.performance;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="font-serif text-3xl">Weekly Intelligence</h1>
        <button onClick={downloadMarkdown} className="text-xs px-3 py-1.5 rounded-md border border-taupedark hover:bg-taupe">
          Export Markdown
        </button>
      </div>
      <p className="text-muted text-sm mb-8">
        {formatDate(report.period.start)} – {formatDate(report.period.end)}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-4 shadow-card">
          <div className="text-[11px] uppercase tracking-wide text-muted mb-1">Occupancy</div>
          <div className="font-serif text-2xl text-bronze">{formatPct(p.occupancy_pct)}</div>
          <div className="text-xs text-muted mt-1">{report.occupancy_change_pts >= 0 ? "+" : ""}{report.occupancy_change_pts} pts vs prior week</div>
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-4 shadow-card">
          <div className="text-[11px] uppercase tracking-wide text-muted mb-1">ADR</div>
          <div className="font-serif text-2xl text-bronze">{formatCurrency(p.adr)}</div>
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-4 shadow-card">
          <div className="text-[11px] uppercase tracking-wide text-muted mb-1">Revenue</div>
          <div className="font-serif text-2xl text-bronze">{formatCurrency(p.gross_revenue)}</div>
          {report.revenue_change_pct !== null && <div className="text-xs text-muted mt-1">{report.revenue_change_pct >= 0 ? "+" : ""}{report.revenue_change_pct}% vs prior week</div>}
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-lg px-5 py-4 shadow-card">
          <div className="text-[11px] uppercase tracking-wide text-muted mb-1">RevPAR</div>
          <div className="font-serif text-2xl text-bronze">{formatCurrency(p.revpar)}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <div className="bg-sage/10 border border-sage/30 rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-wide text-sage mb-1">Biggest opportunity</div>
          <p className="text-sm">{report.biggest_opportunity ? report.biggest_opportunity.action : "No standout opportunity flagged this week."}</p>
        </div>
        <div className="bg-terracotta/10 border border-terracotta/30 rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-wide text-terracotta mb-1">Biggest risk</div>
          <p className="text-sm">{report.biggest_risk ? report.biggest_risk.action : "No red-flag risk currently open."}</p>
        </div>
      </div>

      <h3 className="text-sm font-medium mb-3">Top actions this week</h3>
      <ol className="space-y-2 mb-8 list-decimal pl-5">
        {report.top_actions.map((a: any, i: number) => (
          <li key={i} className="text-sm">
            <span className="uppercase text-[10px] tracking-wide text-bronze mr-1">[{a.category}, {a.confidence}]</span>
            {a.action} <span className="text-muted italic">— {a.expected_impact}</span>
          </li>
        ))}
        {report.top_actions.length === 0 && <p className="text-sm text-muted">No open recommendations — visit the Recommendations page to refresh.</p>}
      </ol>

      <p className="text-xs text-muted">
        Next 7 days forecasted occupancy (based on bookings already on the books): {formatPct(report.next_7_days_forecasted_occupancy_pct)}
      </p>
    </div>
  );
}
