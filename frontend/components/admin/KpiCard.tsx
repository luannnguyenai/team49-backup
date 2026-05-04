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
    <div className="card p-0 transition-colors hover:border-slate-300 dark:hover:border-slate-700">
      <div className="flex h-full flex-col gap-2 p-3.5">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
            {label}
          </p>
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
