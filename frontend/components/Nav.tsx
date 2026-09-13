"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconOverview, IconCalendar, IconBookings, IconRevenue, IconGuests, IconExperience,
  IconCompetitors, IconMarketing, IconForecast, IconInsights, IconReports, IconSettings,
} from "@/components/icons";

const ITEMS = [
  { href: "/", label: "Overview", icon: IconOverview },
  { href: "/calendar", label: "Calendar", icon: IconCalendar },
  { href: "/bookings", label: "Bookings", icon: IconBookings },
  { href: "/revenue", label: "Revenue", icon: IconRevenue },
  { href: "/guests", label: "Guests", icon: IconGuests },
  { href: "/experience", label: "Experience", icon: IconExperience },
  { href: "/competitors", label: "Competitors", icon: IconCompetitors },
  { href: "/marketing", label: "Marketing", icon: IconMarketing },
  { href: "/forecast", label: "Forecast", icon: IconForecast },
  { href: "/insights", label: "Insights", icon: IconInsights },
  { href: "/reports", label: "Reports", icon: IconReports },
  { href: "/settings", label: "Settings", icon: IconSettings },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] shrink-0 bg-warmwhite border-r border-taupedark/50 min-h-screen px-4 py-7 hidden md:flex flex-col">
      <Link href="/" className="mb-9 px-2 block">
        <div className="text-[10px] tracking-widest2 text-bronze uppercase">The Rang</div>
        <div className="font-serif text-[22px] leading-tight text-ink">Intelligence</div>
      </Link>
      <nav className="flex-1 space-y-0.5">
        {ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13.5px] transition-colors ${
                active ? "bg-taupe text-ink font-medium" : "text-muted hover:bg-taupe/60 hover:text-charcoal"
              }`}
            >
              <Icon className={active ? "text-bronze" : "text-muted/80"} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-2.5 pt-4 mt-2 border-t border-taupedark/50">
        <div className="text-[10.5px] text-muted/80 leading-relaxed">
          The Rang Uluwatu
          <br />
          Bali, Indonesia
        </div>
      </div>
    </aside>
  );
}

/** Compact horizontal nav for narrow viewports, where the vertical rail is
 * hidden — keeps every section reachable on mobile without cramming the
 * full sidebar onto a small screen. */
export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="md:hidden flex overflow-x-auto gap-1 px-3 py-2 border-b border-taupedark/50 bg-warmwhite">
      {ITEMS.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs whitespace-nowrap shrink-0 ${
              active ? "bg-taupe text-ink font-medium" : "text-muted"
            }`}
          >
            <Icon className={active ? "text-bronze" : "text-muted/80"} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
