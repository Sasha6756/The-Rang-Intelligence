"use client";

import { useEffect, useState } from "react";
import { apiGet, API_URL } from "@/lib/api";
import { formatPct, formatDate } from "@/lib/format";
import { useCurrency, formatMoney } from "@/lib/currency";

export default function ReportsPage() {
  const { displayCurrency, rateMode, setRateMode, withCurrency } = useCurrency();
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    apiGet(withCurrency("/api/reports/weekly")).then(setReport);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCurrency, rateMode]);

  function downloadMarkdown() {
    const token = localStorage.getItem("rang_token");
    fetch(`${API_URL}${withCurrency("/api/reports/weekly.md")}`, { headers: { Authorization: `Bearer ${token}` } })
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
      <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
        <h1 className="font-serif text-3xl text-ink">Weekly Intelligence</h1>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-taupe/60 rounded-full p-1" title="Current-rate view converts using today's exchange rate; historical-rate view uses the rate effective on each figure's own date.">
            {(["current", "historical"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setRateMode(m)}
                className={`text-[11px] px-3 py-1 rounded-full capitalize ${rateMode === m ? "bg-warmwhite shadow-card text-ink" : "text-muted"}`}
              >
                {m} rates
              </button>
            ))}
          </div>
          <button onClick={downloadMarkdown} className="text-xs px-3.5 py-1.5 rounded-full border border-taupedark hover:bg-taupe">
            Export Markdown
          </button>
        </div>
      </div>
      <p className="text-muted text-sm mb-8">
        {formatDate(report.period.start)} – {formatDate(report.period.end)}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
          <div className="text-[10.5px] uppercase tracking-wide text-muted mb-1.5">Occupancy</div>
          <div className="font-serif text-2xl text-ink tnum">{formatPct(p.occupancy_pct)}</div>
          <div className="text-xs text-muted mt-1.5">{report.occupancy_change_pts >= 0 ? "+" : ""}{report.occupancy_change_pts} pts vs prior week</div>
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
          <div className="text-[10.5px] uppercase tracking-wide text-muted mb-1.5">ADR</div>
          <div className="font-serif text-2xl text-ink tnum">{formatMoney(p.adr, displayCurrency)}</div>
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
          <div className="text-[10.5px] uppercase tracking-wide text-muted mb-1.5">Revenue</div>
          <div className="font-serif text-2xl text-ink tnum">{formatMoney(p.gross_revenue, displayCurrency)}</div>
          {report.revenue_change_pct !== null && <div className="text-xs text-muted mt-1.5">{report.revenue_change_pct >= 0 ? "+" : ""}{report.revenue_change_pct}% vs prior week</div>}
        </div>
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl px-5 py-4">
          <div className="text-[10.5px] uppercase tracking-wide text-muted mb-1.5">RevPAR</div>
          <div className="font-serif text-2xl text-ink tnum">{formatMoney(p.revpar, displayCurrency)}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <div className="bg-sage/8 border border-sage/25 rounded-2xl p-5">
          <div className="text-[10.5px] uppercase tracking-wide text-sage mb-1.5">Biggest opportunity</div>
          <p className="text-sm text-charcoal">{report.biggest_opportunity ? report.biggest_opportunity.action : "No standout opportunity flagged this week."}</p>
        </div>
        <div className="bg-terracotta/8 border border-terracotta/25 rounded-2xl p-5">
          <div className="text-[10.5px] uppercase tracking-wide text-terracotta mb-1.5">Biggest risk</div>
          <p className="text-sm text-charcoal">{report.biggest_risk ? report.biggest_risk.action : "No red-flag risk currently open."}</p>
        </div>
      </div>

      <h3 className="text-sm font-medium text-ink mb-3">Top actions this week</h3>
      <ol className="space-y-2 mb-8 list-decimal pl-5">
        {report.top_actions.map((a: any, i: number) => (
          <li key={i} className="text-sm text-charcoal">
            <span className="uppercase text-[10px] tracking-wide text-bronze mr-1">[{a.category}, {a.confidence}]</span>
            {a.action} <span className="text-muted italic">— {a.expected_impact}</span>
          </li>
        ))}
        {report.top_actions.length === 0 && <p className="text-sm text-muted">No open recommendations — visit Insights to refresh.</p>}
      </ol>

      <p className="text-xs text-muted">
        Next 7 days forecasted occupancy (based on bookings already on the books): {formatPct(report.next_7_days_forecasted_occupancy_pct)}
      </p>
    </div>
  );
}
