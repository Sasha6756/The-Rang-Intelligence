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
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function runPreview() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      form.append("source_type", sourceType);
      form.append("file", file);
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
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("source_type", sourceType);
      form.append("mapping", JSON.stringify(mapping));
      form.append("file", file);
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
    <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-6 shadow-card">
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
            className="border border-taupedark rounded-md px-3 py-2 text-sm bg-white"
          >
            {SOURCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
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
        <button
          onClick={runPreview}
          disabled={!file || loading}
          className="text-xs px-4 py-2 rounded-md bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50"
        >
          {loading ? "Working…" : "Preview"}
        </button>
      </div>

      {error && <p className="text-sm text-terracotta mb-3">{error}</p>}

      {result && (
        <div className="bg-sage/10 border border-sage/30 rounded-md px-4 py-3 text-sm mb-4">
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
                    className="flex-1 border border-taupedark rounded-md px-2 py-1 bg-white text-sm"
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

          <div className="overflow-x-auto mb-4 border border-taupedark/40 rounded-md">
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

          <button onClick={runCommit} disabled={loading} className="text-xs px-4 py-2 rounded-md bg-charcoal text-warmwhite hover:bg-bronzedark disabled:opacity-50">
            {loading ? "Importing…" : `Confirm & import ${preview.valid_row_count} rows`}
          </button>
        </div>
      )}
    </div>
  );
}
