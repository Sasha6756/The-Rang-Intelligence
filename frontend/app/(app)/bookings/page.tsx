"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import ImportWizard from "@/components/ImportWizard";

function monthBounds(offset: number) {
  const d = new Date();
  d.setMonth(d.getMonth() + offset, 1);
  const start = new Date(d.getFullYear(), d.getMonth(), 1);
  const end = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  return { start, end };
}
const iso = (d: Date) => d.toISOString().slice(0, 10);

export default function BookingsPage() {
  const [tab, setTab] = useState<"calendar" | "import">("calendar");
  const [monthOffset, setMonthOffset] = useState(0);
  const [days, setDays] = useState<any[]>([]);
  const [reservations, setReservations] = useState<any[]>([]);

  function loadCalendar() {
    const { start, end } = monthBounds(monthOffset);
    apiGet(`/api/reservations/calendar?start=${iso(start)}&end=${iso(end)}`).then(setDays);
  }

  useEffect(() => {
    loadCalendar();
  }, [monthOffset]);

  useEffect(() => {
    apiGet("/api/reservations").then((r: any[]) => setReservations(r.slice(0, 40)));
  }, [tab]);

  const { start } = monthBounds(monthOffset);
  const monthLabel = start.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const leadingBlanks = start.getDay();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-serif text-3xl">Bookings</h1>
        <div className="flex gap-1 bg-taupe/60 rounded-md p-1">
          <button onClick={() => setTab("calendar")} className={`text-xs px-3 py-1.5 rounded-md ${tab === "calendar" ? "bg-warmwhite shadow-card" : "text-muted"}`}>Calendar</button>
          <button onClick={() => setTab("import")} className={`text-xs px-3 py-1.5 rounded-md ${tab === "import" ? "bg-warmwhite shadow-card" : "text-muted"}`}>Import data</button>
        </div>
      </div>

      {tab === "import" && <ImportWizard onImported={loadCalendar} />}

      {tab === "calendar" && (
        <>
          <div className="bg-warmwhite border border-taupedark/50 rounded-lg p-5 shadow-card mb-8">
            <div className="flex items-center justify-between mb-4">
              <button onClick={() => setMonthOffset((o) => o - 1)} className="text-xs px-2 py-1 rounded hover:bg-taupe">← Prev</button>
              <h3 className="text-sm font-medium">{monthLabel}</h3>
              <button onClick={() => setMonthOffset((o) => o + 1)} className="text-xs px-2 py-1 rounded hover:bg-taupe">Next →</button>
            </div>
            <div className="grid grid-cols-7 gap-1.5 text-center text-[10px] text-muted uppercase mb-1">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => <div key={d}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1.5">
              {Array.from({ length: leadingBlanks }).map((_, i) => <div key={`b${i}`} />)}
              {days.map((day) => (
                <div
                  key={day.date}
                  title={day.is_booked ? `Booked · ADR ${formatCurrency(day.adr)}` : "Available"}
                  className={`aspect-square rounded-md flex flex-col items-center justify-center text-xs ${
                    day.is_booked ? "bg-bronze/20 border border-bronze/40" : "bg-taupe/30 border border-taupedark/30"
                  }`}
                >
                  <span>{new Date(day.date).getDate()}</span>
                  {day.is_booked && <span className="text-[9px] text-bronzedark">●</span>}
                </div>
              ))}
            </div>
            <div className="flex gap-4 mt-4 text-xs text-muted">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-bronze/20 border border-bronze/40 inline-block" /> Booked</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-taupe/30 border border-taupedark/30 inline-block" /> Available</span>
            </div>
          </div>

          <h3 className="text-sm font-medium mb-3">Recent reservations</h3>
          <div className="overflow-x-auto border border-taupedark/40 rounded-lg">
            <table className="text-xs w-full">
              <thead className="bg-taupe/50">
                <tr>
                  {["Channel", "Guest country", "Arrival", "Departure", "Nights", "ADR", "Gross", "Status"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reservations.map((r) => (
                  <tr key={r.id} className="border-t border-taupedark/30">
                    <td className="px-3 py-2">{r.channel_name}</td>
                    <td className="px-3 py-2">{r.guest_country || "—"}</td>
                    <td className="px-3 py-2">{formatDate(r.arrival_date)}</td>
                    <td className="px-3 py-2">{formatDate(r.departure_date)}</td>
                    <td className="px-3 py-2">{r.nights}</td>
                    <td className="px-3 py-2">{formatCurrency(r.adr)}</td>
                    <td className="px-3 py-2">{formatCurrency(r.gross_revenue)}</td>
                    <td className="px-3 py-2 capitalize">{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
