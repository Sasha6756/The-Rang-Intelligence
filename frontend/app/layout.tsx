import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Rang Intelligence",
  description: "Luxury Villa Revenue, Guest & Experience Intelligence Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-cream text-charcoal min-h-screen">{children}</body>
    </html>
  );
}
