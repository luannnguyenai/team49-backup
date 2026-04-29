import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",   // ← brand primary (cyan-led)
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
          950: "#083344",
        },
        brand: {
          indigo: "#4f46e5",
          cyan:   "#06b6d4",
          teal:   "#2dd4bf",
          ink:    "#020617",
        },
        surface: {
          page:           "var(--surface-page)",
          card:           "var(--surface-card)",
          elevated:       "var(--surface-elevated)",
          "accent-soft":  "var(--surface-accent-soft)",
        },
        text: {
          strong: "var(--text-strong)",
          body:   "var(--text-body)",
          muted:  "var(--text-muted-2)",
        },
        border: {
          subtle: "var(--border-subtle)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-in": "slideIn 0.25s ease-out",
        "slide-in-right": "slideInRight 0.25s ease-out",
        "spin-slow": "spin 2s linear infinite",
      },
      borderRadius: {
        card: "28px",
        "card-lg": "32px",
        "card-sm": "24px",
      },
      boxShadow: {
        card: "0 18px 55px rgba(15,23,42,0.08)",
        "card-hover": "0 24px 70px rgba(15,23,42,0.12)",
        "brand-soft": "0 20px 60px -30px rgba(8,145,178,0.32)",
      },
      letterSpacing: {
        "widest-xs": "0.16em",
        "widest-sm": "0.22em",
        "widest-md": "0.24em",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
