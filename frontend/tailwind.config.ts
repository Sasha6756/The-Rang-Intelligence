import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#FAF7F2",
        warmwhite: "#FFFDF9",
        charcoal: "#2B2825",
        taupe: "#EFE9E1",
        taupedark: "#DCD3C6",
        bronze: "#A47B4E",
        bronzedark: "#8A6539",
        sage: "#6E7A64",
        terracotta: "#B5654A",
        muted: "#8A8378",
      },
      fontFamily: {
        serif: ["Georgia", "Iowan Old Style", "Times New Roman", "serif"],
        sans: ["-apple-system", "Inter", "Helvetica Neue", "Arial", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(43,40,37,0.04), 0 4px 16px rgba(43,40,37,0.05)",
      },
    },
  },
  plugins: [],
};
export default config;
