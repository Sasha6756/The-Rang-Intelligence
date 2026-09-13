import { formatMoney } from "@/lib/currency";

/** @deprecated prefer formatMoney from lib/currency directly — kept so
 * existing call sites (value, currencyCode) keep working unchanged while
 * picking up the refined Rp/A$/$/€ formatting. */
export function formatCurrency(value: number | null | undefined, currency = "IDR"): string {
  return formatMoney(value, currency);
}

export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  return d.toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateShort(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  return d.toLocaleDateString("en-US", { day: "numeric", month: "short" });
}
