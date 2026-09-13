"use client";

import { createContext, useContext, useMemo, useState } from "react";

export const RANGE_PRESETS = [
  { key: "7d", label: "7 days", days: 7 },
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
  { key: "365d", label: "12 months", days: 365 },
] as const;

export type RangePresetKey = (typeof RANGE_PRESETS)[number]["key"];

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

interface DateRangeContextValue {
  presetKey: RangePresetKey;
  setPresetKey: (k: RangePresetKey) => void;
  start: string;
  end: string;
  label: string;
}

const DateRangeContext = createContext<DateRangeContextValue | null>(null);

export function DateRangeProvider({ children }: { children: React.ReactNode }) {
  const [presetKey, setPresetKey] = useState<RangePresetKey>("30d");

  const value = useMemo<DateRangeContextValue>(() => {
    const preset = RANGE_PRESETS.find((p) => p.key === presetKey) || RANGE_PRESETS[1];
    return {
      presetKey,
      setPresetKey,
      start: isoDaysAgo(preset.days),
      end: todayIso(),
      label: preset.label,
    };
  }, [presetKey]);

  return <DateRangeContext.Provider value={value}>{children}</DateRangeContext.Provider>;
}

export function useDateRange(): DateRangeContextValue {
  const ctx = useContext(DateRangeContext);
  if (!ctx) throw new Error("useDateRange must be used within a DateRangeProvider");
  return ctx;
}
