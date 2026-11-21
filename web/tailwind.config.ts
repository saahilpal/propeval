import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#FAFAFA",
        surface: "#FFFFFF",
        ink: {
          primary: "#111827",
          secondary: "#4B5563",
          muted: "#9CA3AF",
        },
        border: "#E5E7EB",
        accent: {
          emerald: "#047857",
          emeraldBg: "#ECFDF5",
          crimson: "#B91C1C",
          crimsonBg: "#FEF2F2",
          amber: "#B45309",
          amberBg: "#FFFBEB",
          cobalt: "#1D4ED8",
          cobaltBg: "#EFF6FF",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["IBM Plex Mono", "Menlo", "Monaco", "Consolas", "Courier New", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
