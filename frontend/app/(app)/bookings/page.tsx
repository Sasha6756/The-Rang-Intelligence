"use client";

import { Fragment, useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useCurrency, formatMoney } from "@/lib/currency";
import ImportWizard from "@/components/ImportWizard";
import CalendarSync from "@/components/CalendarSync";
import RevenueReconciliation from "@/components/RevenueReconciliation";

export default function BookingsPage() {
  const { displayCurrency, rateMode, withCurrency } = useCurrency();
  const [tab, setTab] = useState<"list" | "import">("list");
  const [reservations, setReservations] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);

  function loadReservations() {
    apiGet<any[]>(withCurrency("/api/reservations")).then((r) => setReservations(r.slice().reverse().slice(0, 60)));
  }

  useEffect(() => {
    loadReservations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayCurrency, rateMode]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-3xl text-ink">Bookings</h1>
        <div className="flex gap-1 bg-taupe/60 rounded-full p-1">
          <button onClick={() => setTab("list")} className={`text-xs px-3.5 py-1.5 rounded-full ${tab === "list" ? "bg-warmwhite shadow-card text-ink" : "text-muted"}`}>
            Reservations
          </button>
          <button onClick={() => setTab("import")} className={`text-xs px-3.5 py-1.5 rounded-full ${tab === "import" ? "bg-warmwhite shadow-card text-ink" : "text-muted"}`}>
            Import data
          </button>
        </div>
      </div>

      {tab === "import" && (
        <>
          <CalendarSync onSynced={loadReservations} />
          <RevenueReconciliation onReconciled={loadReservations} />
          <ImportWizard onImported={loadReservations} />
        </>
      )}

      {tab === "list" && (
        <div className="bg-warmwhite border border-taupedark/50 rounded-2xl overflow-hidden">
          <table className="text-sm w-full">
            <thead className="bg-taupe/50 text-[10.5px] uppercase tracking-wide text-muted">
              <tr>
                {["Guest", "Dates", "Nights", "Party", "Channel", "Revenue", "ADR", "Status", "Currency"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">
                    {h}
                  </th>
                ))}
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {reservations.map((r) => {
                const isOpen = expanded === r.id;
                return (
                  <Fragment key={r.id}>
                    <tr
                      onClick={() => setExpanded(isOpen ? null : r.id)}
                      className="border-t border-taupedark/30 cursor-pointer hover:bg-cream/60"
                    >
                      <td className="px-4 py-3">
                        <span className="text-charcoal">{r.guest_country || "Guest"}</span>
                        {r.is_calendar_sync && (
                          <span title="Imported from a calendar link — dates only, no price data" className="ml-1.5 text-[9px] uppercase tracking-wide text-bronzedark bg-bronze/15 px-1.5 py-0.5 rounded-full">
                            Calendar
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-charcoal">
                        {formatDate(r.arrival_date)} → {formatDate(r.departure_date)}
                      </td>
                      <td className="px-4 py-3 text-muted">{r.nights}</td>
                      <td className="px-4 py-3 text-muted">
                        {r.adults}A{r.children ? ` · ${r.children}C` : ""}
                      </td>
                      <td className="px-4 py-3 text-charcoal">{r.channel_name}</td>
                      <td className="px-4 py-3 text-charcoal tnum">{formatMoney(r.gross_revenue, displayCurrency)}</td>
                      <td className="px-4 py-3 text-muted tnum">{formatMoney(r.adr, displayCurrency)}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-[10.5px] uppercase tracking-wide px-2 py-0.5 rounded-full ${
                            r.status === "confirmed" ? "bg-sage/15 text-sage" : r.status === "cancelled" ? "bg-terracotta/15 text-terracotta" : "bg-taupe text-muted"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted text-xs uppercase">{displayCurrency}</td>
                      <td className="px-4 py-3 text-muted text-xs">{isOpen ? "▲" : "▼"}</td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-cream/50 border-t border-taupedark/20">
                        <td colSpan={10} className="px-4 py-4">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-xs">
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Booking date</div>
                              <div className="text-charcoal">{r.is_calendar_sync ? "Not available (calendar sync)" : formatDate(r.booking_date)}</div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Lead time</div>
                              <div className="text-charcoal">{r.lead_time_days !== null ? `${r.lead_time_days} days` : "—"}</div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Commission</div>
                              <div className="text-charcoal">{formatMoney(r.commission, displayCurrency)}</div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Net revenue</div>
                              <div className="text-charcoal">{formatMoney(r.net_revenue, displayCurrency)}</div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Original amount</div>
                              <div className="text-charcoal">
                                {r.original_amount != null && r.original_currency
                                  ? formatMoney(r.original_amount, r.original_currency)
                                  : "—"}
                                <span className="text-muted"> (as recorded — never overwritten by display currency)</span>
                              </div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Reference</div>
                              <div className="text-charcoal">{r.external_ref || "—"}</div>
                            </div>
                            <div>
                              <div className="text-muted uppercase tracking-wide text-[10px] mb-0.5">Reservation ID</div>
                              <div className="text-charcoal">#{r.id}</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {reservations.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-muted">
                    No reservations yet — import data or connect a calendar from the Import tab.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
