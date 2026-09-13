"use client";

import Nav, { MobileNav } from "@/components/Nav";
import TopBar from "@/components/TopBar";
import { useAuthGuard } from "@/lib/hooks";
import { CurrencyProvider } from "@/lib/currency";
import { DateRangeProvider } from "@/lib/dateRange";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const ready = useAuthGuard();
  if (!ready) return null;

  return (
    <CurrencyProvider>
      <DateRangeProvider>
        <div className="flex min-h-screen">
          <Nav />
          <div className="flex-1 min-w-0 flex flex-col">
            <TopBar />
            <MobileNav />
            <main className="flex-1 px-4 sm:px-6 md:px-10 py-7 md:py-9 max-w-[1400px] w-full mx-auto">{children}</main>
          </div>
        </div>
      </DateRangeProvider>
    </CurrencyProvider>
  );
}
