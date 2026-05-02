"use client";

// components/admin/KpiCard.tsx
// Glass card with gradient accent border — landing-page design tokens
// (rounded-[28px], backdrop-blur, indigo→cyan→teal gradient).

import { ReactNode } from "react";

type KpiCardProps = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  trend?: "up" | "down" | "flat";
  loading?: boolean;
  children?: ReactNode; // sparkline slot
};

export default function KpiCard({
  label,
  value,
  hint,
  trend,
  loading,
  children,
}: KpiCardProps) {
  return (
    <div className="relative rounded-[28px] bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400 p-[1px] shadow-card transition-shadow hover:shadow-card-hover">
      <div className="flex h-full flex-col gap-3 rounded-[27px] bg-white/80 p-5 backdrop-blur-md dark:bg-slate-900/70">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            {label}
          </p>
          {trend && (
            <span
              className={`text-xs font-semibold ${
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
        <div className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white md:text-4xl">
          {loading ? <span className="inline-block h-9 w-20 animate-pulse rounded bg-slate-200 dark:bg-slate-700" /> : value}
        </div>
        {hint && (
          <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>
        )}
        {children && <div className="mt-2 h-12">{children}</div>}
      </div>
    </div>
  );
}
