export const CHART_PALETTE = {
  primary: "var(--chart-1)",
  secondary: "var(--chart-2)",
  tertiary: "var(--chart-3)",
  quaternary: "var(--chart-4)",
  quinary: "var(--chart-5)",
} as const;

export const CHART_SERIES = [
  CHART_PALETTE.primary,
  CHART_PALETTE.secondary,
  CHART_PALETTE.tertiary,
  CHART_PALETTE.quaternary,
  CHART_PALETTE.quinary,
] as const;

export const CHART_STATUS = {
  success: "var(--state-success-fg)",
  error: "var(--state-error-fg)",
  warning: "var(--state-warning-fg)",
  neutral: "var(--text-muted-2)",
} as const;

export const CHART_GRID = {
  stroke: "var(--border-subtle)",
  tick: "var(--text-muted-2)",
  tooltipBorder: "var(--border-subtle)",
  tooltipBackground: "var(--surface-card)",
} as const;
