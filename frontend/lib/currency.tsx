"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiGet, apiPut } from "@/lib/api";

export const CURRENCIES = [
  { code: "IDR", label: "Indonesian Rupiah", symbol: "Rp" },
  { code: "AUD", label: "Australian Dollar", symbol: "A$" },
  { code: "USD", label: "US Dollar", symbol: "$" },
  { code: "EUR", label: "Euro", symbol: "€" },
] as const;

export type CurrencyCode = (typeof CURRENCIES)[number]["code"];

const SYMBOLS: Record<string, string> = { IDR: "Rp", AUD: "A$", USD: "$", EUR: "€" };
const DECIMALS: Record<string, number> = { IDR: 0, AUD: 2, USD: 2, EUR: 2 };

/** The one money-formatting function the whole app uses — see
 * docs/ARCHITECTURE.md section 11.3. Values arriving here are assumed to
 * already be in `currency` (the backend converts before responding when a
 * `currency` query param is sent), so this only handles presentation:
 * symbol, decimals and thousands separators appropriate to each currency. */
export function formatMoney(value: number | null | undefined, currency: string = "IDR"): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const decimals = DECIMALS[currency] ?? 2;
  const symbol = SYMBOLS[currency] ?? `${currency} `;
  const body = new Intl.NumberFormat("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
  return currency === "IDR" ? `${symbol} ${body}` : `${symbol}${body}`;
}

export interface RateEntry {
  rate: number | null;
  effective_date: string | null;
  retrieved_at: string | null;
  source: string | null;
  is_stale: boolean;
}

export interface RatesStatus {
  base_currency: string;
  today: string;
  currencies: Record<string, RateEntry>;
  has_data: boolean;
  provider: string;
  property_base_currency: string;
  property_default_display_currency: string;
  supported_currencies: string[];
}

type RateMode = "current" | "historical";

interface CurrencyContextValue {
  displayCurrency: string;
  setDisplayCurrency: (code: string) => void;
  rateMode: RateMode;
  setRateMode: (mode: RateMode) => void;
  baseCurrency: string;
  rates: RatesStatus | null;
  refreshRates: () => Promise<void>;
  refreshing: boolean;
  /** Appends `currency=` and `rate_mode=` to an API path so every fetch goes
   * through the same conversion service on the backend (never re-derive a
   * converted number on the frontend). */
  withCurrency: (path: string) => string;
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [displayCurrency, setDisplayCurrencyState] = useState("IDR");
  const [baseCurrency, setBaseCurrency] = useState("IDR");
  const [rateMode, setRateMode] = useState<RateMode>("current");
  const [rates, setRates] = useState<RatesStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const loadRates = useCallback(async () => {
    try {
      const status = await apiGet<RatesStatus>("/api/currency/rates");
      setRates(status);
    } catch {
      /* rates panel just shows "unavailable" — never block the rest of the app */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const prop = await apiGet<any>("/api/property");
        if (cancelled) return;
        setBaseCurrency(prop.currency);
        setDisplayCurrencyState(prop.default_display_currency || prop.currency);
      } catch {
        /* not logged in yet, or property not reachable — defaults stand */
      } finally {
        setInitialized(true);
      }
    })();
    loadRates();
    return () => {
      cancelled = true;
    };
  }, [loadRates]);

  const setDisplayCurrency = useCallback((code: string) => {
    setDisplayCurrencyState(code);
    // Persist as the account's default so it's remembered next session too —
    // fire-and-forget; the UI has already switched instantly either way.
    apiPut("/api/property", { default_display_currency: code }).catch(() => {});
  }, []);

  const refreshRates = useCallback(async () => {
    setRefreshing(true);
    try {
      const { apiPost } = await import("@/lib/api");
      await apiPost("/api/currency/refresh");
      await loadRates();
    } finally {
      setRefreshing(false);
    }
  }, [loadRates]);

  const withCurrency = useCallback(
    (path: string) => {
      const sep = path.includes("?") ? "&" : "?";
      return `${path}${sep}currency=${displayCurrency}&rate_mode=${rateMode}`;
    },
    [displayCurrency, rateMode]
  );

  const value = useMemo<CurrencyContextValue>(
    () => ({ displayCurrency, setDisplayCurrency, rateMode, setRateMode, baseCurrency, rates, refreshRates, refreshing, withCurrency }),
    [displayCurrency, setDisplayCurrency, rateMode, baseCurrency, rates, refreshRates, refreshing, withCurrency]
  );

  if (!initialized) return null;
  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error("useCurrency must be used within a CurrencyProvider");
  return ctx;
}
