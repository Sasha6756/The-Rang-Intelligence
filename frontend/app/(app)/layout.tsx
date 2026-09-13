"use client";

import Nav from "@/components/Nav";
import { useAuthGuard } from "@/lib/hooks";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const ready = useAuthGuard();
  if (!ready) return null;

  return (
    <div className="flex">
      <Nav />
      <main className="flex-1 px-10 py-8 max-w-6xl">{children}</main>
    </div>
  );
}
