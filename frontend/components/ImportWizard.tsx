"use client";

import { useState } from "react";
import { API_URL } from "@/lib/api";

const SOURCE_OPTIONS = [
  { value: "booking_com", label: "Booking.com — reservations" },
  { value: "airbnb", label: "Airbnb — reservations" },
  { value: "direct", label: "Direct bookings — reservations" },
  { value: "reviews_booking_com", label: "Booking.com — reviews" },
  { value: "reviews_airbnb", label: "Airbnb — reviews" },
  { value: "reviews_google", label: "Google — reviews" },
  { value: "reviews_direct", label: "Direct guest feedback" },
  { value: "competitor_rates", label: "Competitor rates (CSV)" },
];

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("rang_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function ImportWizard({ onImported }: { onImported?: () => void }) {
  const [sourceType, setSourceType] = useState("booking_com");
  const [mode, setMode] = useState<"file" | "sheet">("file");
  const [file, setFile] = useState<File | null>(null);
  const [sheetUrl, setSheetUrl] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const hasInput = mode === "file" ? !!file : sheetUrl.trim().length > 0;

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
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const form = buildForm();
      const res = await fetch(`${API_URL}/api/imports/preview`, { method: "POST", headers: authHeaders(), body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Preview failed");
      const data = await res.json();
      setPreview(data);
      setMapping(data.suggested_mapping);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runCommit() {
    if (!hasInput) return;
    setLoading(true);
    setError(null);
    try {
      const form = buildForm({ mapping: JSON.stringify(mapping) });
      const res = await fetch(`${API_URL}/api/imports/commit`, { method: "POST", headers: authHeaders(), body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Import failed");
      const data = await res.json();
      setResult(data);
      setPreview(null);
      onImported?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 shadow-card">
      <h3 className="text-sm font-medium mb-4">Import data</h3>

      <div className="flex flex-wrap gap-3 items-end mb-4">
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Data source</label>
          <select
            value={sourceType}
            onChange={(e) => {
              setSourceType(e.target.value);
              setPreview(null);
              setResult(null);
            }}
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
              onClick={() => { setMode("file"); setPreview(null); setResult(null); }}
              className={`px-3 py-2 ${mode === "file" ? "bg-charcoal text-warmwhite" : "bg-white text-charcoal"}`}
            >
              Upload a file
            </button>
            <button
              type="button"
              onClick={() => { setMode("sheet"); setPreview(null); setResult(null); }}
              className={`px-3 py-2 ${mode === "sheet" ? "bg-charcoal text-warmwhite" : "bg-white text-charcoal"}`}
            >
              Google Sheet link
            </button>
          </div>
        </div>

        {mode === "file" ? (
          <div>
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">File (.csv or .xlsx)</label>
            <input
              type="file"
              accept=".csv,.xlsx,.xlsm"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setPreview(null);
                setResult(null);
              }}
              className="text-sm"
            />
          </div>
        ) : (
          <div className="flex-1 min-w-[18rem]">
            <label className="block text-[11px] uppercase tracking-wide text-muted mb-1">Google Sheet link</label>
            <input
              type="url"
              value={sheetUrl}
              onChange={(e) => { setSheetUrl(e.target.value); setPreview(null); setResult(null); }}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              className="w-full border border-taupedark rounded-lg px-3 py-2 text-sm bg-white"
            />
          </div>
        )}

        <button
          onClick={runPreview}
          disabled={!hasInput || loading}
          className="text-xs px-4 py-2 rounded-lg bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50"
        >
          {loading ? "Working…" : "Preview"}
        </button>
      </div>

      {mode === "sheet" && (
        <p className="text-xs text-muted mb-4 -mt-2">
          The sheet needs to be shared as "Anyone with the link" (Viewer) — in Google Sheets, click Share, change
          access, then paste the link above. We only read it, nothing is ever written back to your sheet.
        </p>
      )}

      {error && <p className="text-sm text-terracotta mb-3">{error}</p>}

      {result && (
        <div className="bg-sage/10 border border-sage/30 rounded-lg px-4 py-3 text-sm mb-4">
          Imported {result.rows_imported} rows.
          {result.warnings.length > 0 && (
            <details className="mt-1 text-xs text-muted">
              <summary className="cursor-pointer">{result.warnings.length} warnings</summary>
              <ul className="list-disc pl-4 mt-1 space-y-0.5">
                {result.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}

      {preview && (
        <div>
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

          <button onClick={runCommit} disabled={loading} className="text-xs px-4 py-2 rounded-lg bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50">
            {loading ? "Importing…" : `Confirm & import ${preview.valid_row_count} rows`}
          </button>
        </div>
      )}
    </div>
  );
}
