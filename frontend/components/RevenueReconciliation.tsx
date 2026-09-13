"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const SOURCE_OPTIONS = [
  { value: "booking_com", label: "Booking.com — payout / earnings report" },
  { value: "airbnb", label: "Airbnb — payout / earnings report" },
  { value: "direct", label: "Direct bookings — revenue report" },
];

type Candidate = {
  reservation_id: number;
  reason: string;
  arrival_date: string;
  departure_date: string;
  nights: number;
  external_ref: string;
  already_priced: boolean;
  current_gross_revenue: number | null;
  is_calendar_sync: boolean;
};

type MatchRow = {
  row_index: number;
  parsed: {
    external_ref: string;
    arrival_date: string;
    departure_date: string;
    guest_name: string;
    gross_revenue: number;
    commission: number;
    currency: string;
  };
  candidates: Candidate[];
  suggested_reservation_id: number | null;
};

type Decision = { action: "match" | "create_new" | "skip"; reservation_id: number | null };

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("rang_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function postForm(path: string, form: FormData) {
  const res = await fetch(`${API_URL}${path}`, { method: "POST", headers: authHeaders(), body: form });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export default function RevenueReconciliation({ onReconciled }: { onReconciled?: () => void }) {
  const [sourceType, setSourceType] = useState("airbnb");
  const [mode, setMode] = useState<"file" | "sheet">("file");
  const [file, setFile] = useState<File | null>(null);
  const [sheetUrl, setSheetUrl] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [matchData, setMatchData] = useState<{ matches: MatchRow[]; warnings: string[]; unmatched_count: number } | null>(null);
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [loading, setLoading] = useState<"preview" | "match" | "commit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const hasInput = mode === "file" ? !!file : sheetUrl.trim().length > 0;

  function reset() {
    setPreview(null);
    setMatchData(null);
    setDecisions({});
    setResult(null);
    setError(null);
  }

  function buildForm(extra?: Record<string, string>) {
    const form = new FormData();
    form.append("source_type", sourceType);
    if (mode === "sheet") {
      form.append("sheet_url", sheetUrl.trim());
    } else if (file) {
      form.append("file", file);
    }
    if (extra) {
      for (const [k, v] of Object.entries(extra)) form.append(k, v);
    }
    return form;
  }

  async function runPreview() {
    if (!hasInput) return;
    setLoading("preview");
    setError(null);
    setResult(null);
    setMatchData(null);
    try {
      const form = buildForm();
      const data = await postForm("/api/revenue/preview", form);
      setPreview(data);
      setMapping(data.suggested_mapping);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(null);
    }
  }

  async function runMatch() {
    if (!hasInput) return;
    setLoading("match");
    setError(null);
    try {
      const form = buildForm({ mapping: JSON.stringify(mapping) });
      const data = await postForm("/api/revenue/match", form);
      setMatchData(data);
      const initial: Record<number, Decision> = {};
      for (const m of data.matches as MatchRow[]) {
        initial[m.row_index] = m.suggested_reservation_id
          ? { action: "match", reservation_id: m.suggested_reservation_id }
          : { action: "create_new", reservation_id: null };
      }
      setDecisions(initial);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(null);
    }
  }

  async function runCommit() {
    if (!hasInput || !matchData) return;
    setLoading("commit");
    setError(null);
    try {
      const form = buildForm({
        mapping: JSON.stringify(mapping),
        decisions: JSON.stringify(matchData.matches.map((m) => ({ row_index: m.row_index, ...decisions[m.row_index] }))),
      });
      const data = await postForm("/api/revenue/commit", form);
      setResult(data);
      setPreview(null);
      setMatchData(null);
      onReconciled?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(null);
    }
  }

  function setDecision(rowIndex: number, patch: Partial<Decision>) {
    setDecisions((d) => ({ ...d, [rowIndex]: { ...d[rowIndex], ...patch } }));
  }

  return (
    <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 shadow-card mb-6">
      <h3 className="text-sm font-medium mb-1">Reconcile revenue / payout report</h3>
      <p className="text-xs text-muted mb-4">
        Upload a payout or earnings report (CSV, Excel, or PDF) and match each line to the right booking —
        useful for filling in prices on bookings that came in from a calendar sync with no revenue figure.
        Nothing is saved until you confirm each match below.
      </p>

      <div className="flex flex-wrap gap-3 items-end mb-4">
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Report source</label>
          <select
            value={sourceType}
            onChange={(e) => { setSourceType(e.target.value); reset(); }}
            className="border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Source</label>
          <div className="flex rounded-lg border border-taupedark overflow-hidden text-xs">
            <button
              type="button"
              onClick={() => { setMode("file"); reset(); }}
              className={`px-3 py-2 ${mode === "file" ? "bg-charcoal text-warmwhite" : "bg-white text-charcoal"}`}
            >
              Upload a file
            </button>
            <button
              type="button"
              onClick={() => { setMode("sheet"); reset(); }}
              className={`px-3 py-2 ${mode === "sheet" ? "bg-charcoal text-warmwhite" : "bg-white text-charcoal"}`}
            >
              Google Sheet link
            </button>
          </div>
        </div>

        {mode === "file" ? (
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">File (.csv, .xlsx or .pdf)</label>
            <input
              type="file"
              accept=".csv,.xlsx,.xlsm,.pdf"
              onChange={(e) => { setFile(e.target.files?.[0] || null); reset(); }}
              className="text-sm"
            />
          </div>
        ) : (
          <div className="flex-1 min-w-[18rem]">
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Google Sheet link</label>
            <input
              type="url"
              value={sheetUrl}
              onChange={(e) => { setSheetUrl(e.target.value); reset(); }}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              className="w-full border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
            />
          </div>
        )}

        <button
          onClick={runPreview}
          disabled={!hasInput || loading !== null}
          className="text-xs px-4 py-2 rounded-lg bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50"
        >
          {loading === "preview" ? "Reading…" : "Preview"}
        </button>
      </div>

      {mode === "sheet" && (
        <p className="text-xs text-muted mb-4 -mt-2">
          The sheet needs to be shared as "Anyone with the link" (Viewer) — in Google Sheets, click Share, change
          access, then paste the link above. If your spreadsheet has more than one tab, click on the specific tab
          with your payout data first, then copy the link from your browser's address bar — that way it opens the
          right one instead of whichever tab happens to be first. We only read it, nothing is ever written back
          to your sheet.
        </p>
      )}

      {error && <p className="text-sm text-terracotta mb-3">{error}</p>}

      {result && (
        <div className="bg-sage/10 border border-sage/30 rounded-lg px-4 py-3 text-sm mb-4">
          Matched {result.matched} to existing bookings, created {result.created} new bookings, skipped {result.skipped}.
          {result.errors?.length > 0 && (
            <details className="mt-1 text-xs text-terracotta">
              <summary className="cursor-pointer">{result.errors.length} errors</summary>
              <ul className="list-disc pl-4 mt-1 space-y-0.5">
                {result.errors.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}

      {preview && !matchData && (
        <div>
          {preview.pdf_warning && (
            <p className="text-xs bg-bronze/10 border border-bronze/30 rounded-lg px-3 py-2 mb-3 text-bronzedark">
              {preview.pdf_warning}
            </p>
          )}
          <p className="text-xs text-muted mb-2">
            {preview.row_count} rows detected · {preview.valid_row_count} look valid with the current mapping
            {preview.total_warning_count > 0 && ` · ${preview.total_warning_count} warnings`}
          </p>

          <div className="mb-4">
            <div className="text-[11px] uppercase tracking-wide text-muted mb-2">Column mapping — your column → system field</div>
            <div className="grid sm:grid-cols-2 gap-2">
              {preview.system_fields.map((field: string) => (
                <div key={field} className="flex items-center gap-2 text-sm">
                  <span className="w-40 shrink-0 text-muted">{field}</span>
                  <span className="text-muted">→</span>
                  <select
                    value={mapping[field] || ""}
                    onChange={(e) => setMapping({ ...mapping, [field]: e.target.value || null })}
                    className="flex-1 border border-taupedark rounded-lg px-2 py-1 bg-white text-sm"
                  >
                    <option value="">— not mapped —</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {preview.warnings.length > 0 && (
            <details className="mb-4 text-xs text-muted">
              <summary className="cursor-pointer">{preview.warnings.length}+ validation warnings with current mapping</summary>
              <ul className="list-disc pl-4 mt-1 space-y-0.5 max-h-32 overflow-auto">
                {preview.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          <div className="overflow-x-auto mb-4 border border-taupedark/40 rounded-lg">
            <table className="text-xs w-full">
              <thead className="bg-taupe/50">
                <tr>{preview.headers.map((h: string) => <th key={h} className="px-2 py-1.5 text-left font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row: any, i: number) => (
                  <tr key={i} className="border-t border-taupedark/30">
                    {preview.headers.map((h: string) => <td key={h} className="px-2 py-1.5">{row[h]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button onClick={runMatch} disabled={loading !== null} className="text-xs px-4 py-2 rounded-lg bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50">
            {loading === "match" ? "Finding matches…" : `Find matches for ${preview.valid_row_count} rows`}
          </button>
        </div>
      )}

      {matchData && (
        <div>
          <p className="text-xs text-muted mb-3">
            {matchData.matches.length} rows · {matchData.unmatched_count} with no candidate booking found.
            Check each row below — nothing is saved until you confirm.
          </p>

          <div className="space-y-3 mb-4">
            {matchData.matches.map((m) => {
              const decision = decisions[m.row_index] || { action: "skip" as const, reservation_id: null };
              return (
                <div key={m.row_index} className="border border-taupedark/30 rounded-lg p-3">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs mb-2">
                    <span className="font-medium">{m.parsed.guest_name || "(no name)"}</span>
                    <span className="text-muted">{formatDate(m.parsed.arrival_date)} → {formatDate(m.parsed.departure_date)}</span>
                    <span className="text-muted">{formatCurrency(m.parsed.gross_revenue)} gross</span>
                    {m.parsed.external_ref && <span className="text-muted">ref: {m.parsed.external_ref}</span>}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={decision.action === "match" ? String(decision.reservation_id) : decision.action}
                      onChange={(e) => {
                        const v = e.target.value;
                        if (v === "create_new" || v === "skip") setDecision(m.row_index, { action: v, reservation_id: null });
                        else setDecision(m.row_index, { action: "match", reservation_id: Number(v) });
                      }}
                      className="flex-1 min-w-[16rem] border border-taupedark rounded-lg px-2 py-1.5 bg-white text-xs"
                    >
                      {m.candidates.length === 0 && <option value="skip">No candidate bookings found</option>}
                      {m.candidates.map((c) => (
                        <option key={c.reservation_id} value={c.reservation_id}>
                          {formatDate(c.arrival_date)} → {formatDate(c.departure_date)} ({c.nights}n) — {c.reason}
                          {c.already_priced ? ` — already priced at ${formatCurrency(c.current_gross_revenue)}` : ""}
                        </option>
                      ))}
                      <option value="create_new">— Create a new booking for this row —</option>
                      <option value="skip">— Skip this row —</option>
                    </select>
                  </div>

                  {decision.action === "match" && (() => {
                    const cand = m.candidates.find((c) => c.reservation_id === decision.reservation_id);
                    return cand?.already_priced ? (
                      <p className="text-[11px] text-bronzedark mt-1.5">
                        This booking already has a price of {formatCurrency(cand.current_gross_revenue)} — confirming will overwrite it.
                      </p>
                    ) : null;
                  })()}
                </div>
              );
            })}
          </div>

          {matchData.warnings.length > 0 && (
            <details className="mb-4 text-xs text-muted">
              <summary className="cursor-pointer">{matchData.warnings.length} validation warnings</summary>
              <ul className="list-disc pl-4 mt-1 space-y-0.5 max-h-32 overflow-auto">
                {matchData.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}

          <div className="flex gap-2">
            <button onClick={runCommit} disabled={loading !== null} className="text-xs px-4 py-2 rounded-lg bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50">
              {loading === "commit" ? "Saving…" : "Confirm & save"}
            </button>
            <button onClick={() => setMatchData(null)} disabled={loading !== null} className="text-xs px-4 py-2 rounded-lg border border-taupedark text-charcoal disabled:opacity-50">
              Back to mapping
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
