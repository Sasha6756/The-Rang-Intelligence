"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";

const CHANNELS = [
  { key: "airbnb", label: "Airbnb" },
  { key: "booking_com", label: "Booking.com" },
];

type FeedStatus = {
  channel: string | null;
  url: string;
  last_synced_at: string | null;
  last_sync_status: string;
  last_sync_message: string;
};

export default function CalendarSync({ onSynced }: { onSynced?: () => void }) {
  const [urls, setUrls] = useState<Record<string, string>>({ airbnb: "", booking_com: "" });
  const [statusByChannel, setStatusByChannel] = useState<Record<string, FeedStatus>>({});
  const [syncing, setSyncing] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, string>>({});

  function loadStatus() {
    apiGet<FeedStatus[]>("/api/imports/ical/status").then((feeds) => {
      const byLabel: Record<string, FeedStatus> = {};
      const prefill: Record<string, string> = { airbnb: "", booking_com: "" };
      for (const f of feeds) {
        const key = f.channel === "Airbnb" ? "airbnb" : f.channel === "Booking.com" ? "booking_com" : null;
        if (!key) continue;
        byLabel[key] = f;
        prefill[key] = f.url;
      }
      setStatusByChannel(byLabel);
      setUrls((prev) => ({ ...prev, ...prefill }));
    }).catch(() => {});
  }

  useEffect(() => {
    loadStatus();
  }, []);

  async function sync(channel: string) {
    const url = (urls[channel] || "").trim();
    if (!url) {
      setErrors((e) => ({ ...e, [channel]: "Paste a calendar link first." }));
      return;
    }
    setSyncing(channel);
    setErrors((e) => ({ ...e, [channel]: "" }));
    setResults((r) => ({ ...r, [channel]: "" }));
    try {
      const res = await apiPost(`/api/imports/ical/sync`, { channel, url });
      setResults((r) => ({
        ...r,
        [channel]: `Synced: ${res.created} new, ${res.updated} updated, ${res.cancelled} cancelled, ${res.unchanged} unchanged.`,
      }));
      loadStatus();
      onSynced?.();
    } catch (e: any) {
      setErrors((er) => ({ ...er, [channel]: e instanceof ApiError ? e.message : "Sync failed." }));
    } finally {
      setSyncing(null);
    }
  }

  return (
    <div className="bg-warmwhite border border-taupedark/50 rounded-2xl p-6 shadow-card mb-6">
      <h3 className="text-sm font-medium mb-1">Connect calendar (Airbnb / Booking.com)</h3>
      <p className="text-xs text-muted mb-4">
        Paste the calendar export link from each platform to keep occupancy up to date automatically. These
        links only carry check-in/check-out dates — no price or guest name — so revenue figures still need a
        CSV export from each platform, but occupancy, length-of-stay and channel mix will reflect real
        bookings immediately.
      </p>

      <div className="space-y-4">
        {CHANNELS.map(({ key, label }) => {
          const status = statusByChannel[key];
          return (
            <div key={key} className="border border-taupedark/30 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium">{label}</span>
                {status?.last_synced_at && (
                  <span className="text-[11px] text-muted">
                    Last synced {formatDate(status.last_synced_at)} ·{" "}
                    <span className={status.last_sync_status === "ok" ? "text-green-700" : "text-red-700"}>
                      {status.last_sync_status === "ok" ? status.last_sync_message : "failed"}
                    </span>
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={urls[key] || ""}
                  onChange={(e) => setUrls((u) => ({ ...u, [key]: e.target.value }))}
                  placeholder={`Paste your ${label} iCal export URL here`}
                  className="flex-1 text-xs border border-taupedark/40 rounded px-2 py-1.5 bg-white"
                />
                <button
                  onClick={() => sync(key)}
                  disabled={syncing === key}
                  className="text-xs px-3 py-1.5 rounded-lg bg-charcoal text-warmwhite disabled:opacity-50"
                >
                  {syncing === key ? "Syncing…" : "Sync now"}
                </button>
              </div>
              {errors[key] && <p className="text-[11px] text-red-700 mt-1.5">{errors[key]}</p>}
              {results[key] && <p className="text-[11px] text-green-700 mt-1.5">{results[key]}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
