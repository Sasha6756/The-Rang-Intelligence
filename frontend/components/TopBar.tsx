"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, clearToken } from "@/lib/api";
import { CURRENCIES, useCurrency } from "@/lib/currency";
import { RANGE_PRESETS, useDateRange } from "@/lib/dateRange";
import { formatDate } from "@/lib/format";
import { IconBell, IconChevronDown, IconSettings, IconSignOut } from "@/components/icons";

function Dropdown({
  trigger,
  children,
  align = "right",
}: {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1.5">
        {trigger}
      </button>
      {open && (
        <div
          className={`absolute top-full mt-2 ${align === "right" ? "right-0" : "left-0"} bg-warmwhite border border-taupedark/50 rounded-xl shadow-lift py-1.5 z-30 min-w-[180px]`}
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export default function TopBar() {
  const router = useRouter();
  const { displayCurrency, setDisplayCurrency, rates } = useCurrency();
  const { presetKey, setPresetKey, label } = useDateRange();
  const [propertyName, setPropertyName] = useState("The Rang Uluwatu");
  const [openCount, setOpenCount] = useState<number | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    apiGet<any>("/api/property").then((p) => setPropertyName(p.name)).catch(() => {});
    apiGet<any[]>("/api/recommendations?status=open").then((recs) => setOpenCount(recs.length)).catch(() => {});
    apiGet<any>("/api/auth/me").then((u) => setUserEmail(u.email)).catch(() => {});
  }, []);

  const rateEntry = displayCurrency !== "IDR" ? rates?.currencies?.[displayCurrency] : null;
  const isStale = rateEntry?.is_stale;

  return (
    <header className="h-16 shrink-0 border-b border-taupedark/50 bg-warmwhite/80 backdrop-blur px-5 md:px-8 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-[10px] tracking-widest2 text-bronze uppercase hidden sm:inline">The Rang</span>
        <span className="text-taupedark hidden sm:inline">·</span>
        <span className="text-sm text-charcoal truncate">{propertyName}</span>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <Dropdown
          trigger={
            <span className="text-xs px-3 py-1.5 rounded-full border border-taupedark/60 text-charcoal hover:bg-taupe/50 flex items-center gap-1.5">
              {label} <IconChevronDown className="text-muted" />
            </span>
          }
        >
          {RANGE_PRESETS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPresetKey(p.key)}
              className={`block w-full text-left px-3.5 py-2 text-xs hover:bg-taupe/50 ${p.key === presetKey ? "text-bronze font-medium" : "text-charcoal"}`}
            >
              {p.label}
            </button>
          ))}
        </Dropdown>

        <Dropdown
          trigger={
            <span className="text-xs px-3 py-1.5 rounded-full border border-taupedark/60 text-charcoal hover:bg-taupe/50 flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${isStale ? "bg-clay" : "bg-sage"}`} />
              {displayCurrency} <IconChevronDown className="text-muted" />
            </span>
          }
        >
          {CURRENCIES.map((c) => (
            <button
              key={c.code}
              onClick={() => setDisplayCurrency(c.code)}
              className={`block w-full text-left px-3.5 py-2 text-xs hover:bg-taupe/50 ${c.code === displayCurrency ? "text-bronze font-medium" : "text-charcoal"}`}
            >
              <span className="inline-block w-9 text-muted">{c.symbol}</span>
              {c.code}
              <span className="text-muted"> · {c.label}</span>
            </button>
          ))}
          <div className="border-t border-taupedark/40 mt-1 pt-1.5 px-3.5 pb-1 text-[10.5px] text-muted leading-relaxed">
            {rates?.has_data
              ? `Rates updated ${formatDate(rates.today)}${isStale ? " · showing last available rate" : ""}`
              : "Rates not fetched yet"}
          </div>
        </Dropdown>

        <button
          onClick={() => router.push("/insights")}
          className="relative w-8 h-8 rounded-full border border-taupedark/60 flex items-center justify-center text-muted hover:bg-taupe/50"
          title="Open recommendations"
        >
          <IconBell />
          {!!openCount && (
            <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-bronze text-warmwhite text-[9px] leading-4 text-center">
              {openCount}
            </span>
          )}
        </button>

        <Dropdown
          trigger={
            <span className="w-8 h-8 rounded-full bg-taupe flex items-center justify-center text-xs font-medium text-charcoal">
              {(userEmail || "?")[0]?.toUpperCase()}
            </span>
          }
        >
          <div className="px-3.5 py-2 text-xs text-muted truncate border-b border-taupedark/40 mb-1">{userEmail}</div>
          <button
            onClick={() => router.push("/settings")}
            className="flex items-center gap-2 w-full text-left px-3.5 py-2 text-xs text-charcoal hover:bg-taupe/50"
          >
            <IconSettings /> Settings
          </button>
          <button
            onClick={() => {
              clearToken();
              router.push("/login");
            }}
            className="flex items-center gap-2 w-full text-left px-3.5 py-2 text-xs text-charcoal hover:bg-taupe/50"
          >
            <IconSignOut /> Sign out
          </button>
        </Dropdown>
      </div>
    </header>
  );
}
