"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const ITEMS = [
  { href: "/", label: "Today" },
  { href: "/revenue", label: "Revenue" },
  { href: "/bookings", label: "Bookings" },
  { href: "/guests", label: "Guests" },
  { href: "/competitors", label: "Competitors" },
  { href: "/experience", label: "Guest Experience" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="w-60 shrink-0 border-r border-taupedark/60 min-h-screen px-5 py-8 flex flex-col">
      <div className="mb-10 px-1">
        <div className="text-[10px] tracking-[0.25em] text-bronze uppercase">The Rang</div>
        <div className="font-serif text-xl">Intelligence</div>
      </div>
      <nav className="flex-1 space-y-0.5">
        {ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-md text-sm transition ${
                active ? "bg-taupe text-charcoal font-medium" : "text-muted hover:bg-taupe/60 hover:text-charcoal"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <button
        onClick={() => {
          clearToken();
          router.push("/login");
        }}
        className="text-xs text-muted hover:text-charcoal text-left px-3 py-2"
      >
        Sign out
      </button>
    </aside>
  );
}
