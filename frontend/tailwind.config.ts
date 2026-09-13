import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Base surfaces
        cream: "#F6F1E7",       // page background — warm ivory
        warmwhite: "#FFFFFF",   // card surfaces
        // Secondary / sunken surfaces & borders
        taupe: "#EFE8D9",
        taupedark: "#DDD2BC",
        // Text
        charcoal: "#221F1B",    // primary text
        ink: "#161310",         // headings, near-black
        muted: "#8C8271",       // secondary text, warm grey
        // Accent — muted sand, never a strong/saturated gold
        bronze: "#A3814F",
        bronzedark: "#84663C",
        // Chart / status — deliberately muted, editorial, never saturated
        sage: "#74805F",        // muted green — positive
        steel: "#6C8299",       // muted blue — neutral
        clay: "#BE8657",        // muted orange — attention
        terracotta: "#A8583F",  // muted rust — negative/risk
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Iowan Old Style", "Georgia", "serif"],
        sans: ["var(--font-sans)", "-apple-system", "Helvetica Neue", "Arial", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(22,19,16,0.04), 0 6px 20px rgba(22,19,16,0.05)",
        lift: "0 2px 4px rgba(22,19,16,0.05), 0 12px 32px rgba(22,19,16,0.08)",
      },
      letterSpacing: {
        widest2: "0.22em",
      },
    },
  },
  plugins: [],
};
export default config;
