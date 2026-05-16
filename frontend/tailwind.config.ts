import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
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
          ink:        "var(--brand-ink)",
          "ink-hover":"var(--brand-ink-hover)",
          "ink-fg":   "var(--brand-ink-fg)",
        },
        glass: {
          DEFAULT:       "var(--glass-bg)",
          hover:         "var(--glass-bg-hover)",
          border:        "var(--glass-border)",
          "border-hover":"var(--glass-border-hover)",
          fg:            "var(--glass-fg)",
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
        bloom: {
          remember: "var(--bloom-remember)",
          "remember-soft": "var(--bloom-remember-soft)",
          understand: "var(--bloom-understand)",
          "understand-soft": "var(--bloom-understand-soft)",
          apply: "var(--bloom-apply)",
          "apply-soft": "var(--bloom-apply-soft)",
          analyze: "var(--bloom-analyze)",
          "analyze-soft": "var(--bloom-analyze-soft)",
          evaluate: "var(--bloom-evaluate)",
          "evaluate-soft": "var(--bloom-evaluate-soft)",
          create: "var(--bloom-create)",
          "create-soft": "var(--bloom-create-soft)",
        },
        session: {
          assessment: "var(--session-assessment)",
          "assessment-soft": "var(--session-assessment-soft)",
          quiz: "var(--session-quiz)",
          "quiz-soft": "var(--session-quiz-soft)",
          "module-test": "var(--session-module-test)",
          "module-test-soft": "var(--session-module-test-soft)",
          practice: "var(--session-practice)",
          "practice-soft": "var(--session-practice-soft)",
        },
        tier: {
          bronze: "var(--tier-bronze)",
          "bronze-soft": "var(--tier-bronze-soft)",
          silver: "var(--tier-silver)",
          "silver-soft": "var(--tier-silver-soft)",
          gold: "var(--tier-gold)",
          "gold-soft": "var(--tier-gold-soft)",
          platinum: "var(--tier-platinum)",
          "platinum-soft": "var(--tier-platinum-soft)",
        },
        stat: {
          courses: "var(--stat-courses)",
          "courses-soft": "var(--stat-courses-soft)",
          progress: "var(--stat-progress)",
          "progress-soft": "var(--stat-progress-soft)",
          time: "var(--stat-time)",
          "time-soft": "var(--stat-time-soft)",
          completed: "var(--stat-completed)",
          "completed-soft": "var(--stat-completed-soft)",
        },
        insight: {
          DEFAULT: "var(--insight-fg)",
          soft: "var(--insight-bg)",
          border: "var(--insight-border)",
        },
        state: {
          "success-bg": "var(--state-success-bg)",
          "success-fg": "var(--state-success-fg)",
          "success-border": "var(--state-success-border)",
          "error-bg": "var(--state-error-bg)",
          "error-fg": "var(--state-error-fg)",
          "error-border": "var(--state-error-border)",
          "warning-bg": "var(--state-warning-bg)",
          "warning-fg": "var(--state-warning-fg)",
          "warning-border": "var(--state-warning-border)",
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
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
          "0%": { opacity: "0", transform: "translateY(8px)" },
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
