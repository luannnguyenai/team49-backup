"use client";

// components/admin/KpiCard.tsx
// Glass card with gradient accent border — landing-page design tokens
// (rounded-[28px], backdrop-blur, indigo→cyan→teal gradient).

import { ReactNode, useState } from "react";

export type KpiTooltip = {
  summary: ReactNode;
  detail: ReactNode;
};

type KpiCardProps = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tooltip?: KpiTooltip;
  trend?: "up" | "down" | "flat";
  loading?: boolean;
  children?: ReactNode; // sparkline slot
};

export default function KpiCard({
  label,
  value,
  hint,
  tooltip,
  trend,
  loading,
  children,
}: KpiCardProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  return (
    <div className="card p-0 transition-colors hover:border-slate-300 dark:hover:border-slate-700">
      <div className="flex h-full flex-col gap-2 p-3.5">
        <div className="flex items-center justify-between">
          <div className="relative flex items-center gap-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              {label}
            </p>
            {tooltip && (
              <>
                <button
                  type="button"
                  aria-label={`More info for ${label}`}
                  className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 text-[10px] font-semibold text-slate-500 transition hover:border-cyan-500 hover:text-cyan-600 focus:border-cyan-500 focus:text-cyan-600 focus:outline-none dark:border-slate-700 dark:text-slate-400"
                  onMouseEnter={() => setTooltipOpen(true)}
                  onMouseLeave={() => setTooltipOpen(false)}
                  onFocus={() => setTooltipOpen(true)}
                  onBlur={() => setTooltipOpen(false)}
                >
                  i
                </button>
                {tooltipOpen && (
                  <div className="absolute left-0 top-5 z-20 w-72 rounded-2xl border border-slate-200 bg-white/95 p-3 text-left shadow-xl backdrop-blur-md dark:border-slate-700 dark:bg-slate-950/95">
                    <p className="text-[11px] font-semibold leading-4 text-slate-800 dark:text-slate-100">
                      {tooltip.summary}
                    </p>
                    <p className="mt-1 text-[11px] leading-4 text-slate-600 dark:text-slate-300">
                      {tooltip.detail}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
          {trend && (
            <span
              className={`text-[10px] font-semibold ${
                trend === "up"
                  ? "text-emerald-600"
                  : trend === "down"
                    ? "text-rose-600"
                    : "text-slate-400"
              }`}
              aria-label={`trend ${trend}`}
            >
              {trend === "up" ? "▲" : trend === "down" ? "▼" : "—"}
            </span>
          )}
        </div>
        <div className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-2xl">
          {loading ? <span className="inline-block h-7 w-14 animate-pulse rounded-md bg-slate-200 dark:bg-slate-700" /> : value}
        </div>
        {hint && (
          <p className="text-[10px] leading-4 text-slate-500 dark:text-slate-400">{hint}</p>
        )}
        {children && <div className="mt-1 h-8">{children}</div>}
      </div>
    </div>
  );
}
