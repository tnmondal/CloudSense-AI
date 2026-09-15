/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0b1220",
          panel: "#111a2e",
          raised: "#16213a",
          border: "#22314f",
        },
        ink: {
          DEFAULT: "#e7ecf5",
          muted: "#93a2c0",
          faint: "#5f6f92",
        },
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          400: "#5b8def",
          500: "#3866d6",
          600: "#2b52ad",
        },
        severity: {
          critical: "#e5484d",
          high: "#f2994a",
          medium: "#e9c46a",
          low: "#6ec3a4",
        },
        positive: "#3fb98a",
        negative: "#e5484d",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.03)",
      },
      borderRadius: {
        xl2: "0.875rem",
      },
    },
  },
  plugins: [],
}

