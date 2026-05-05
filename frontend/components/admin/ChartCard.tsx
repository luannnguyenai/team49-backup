"use client";

// components/admin/ChartCard.tsx
// Glass-style card wrapper for Recharts content with consistent spacing.

import { ReactNode } from "react";

type ChartCardProps = {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  height?: number;
  children: ReactNode;
};

export default function ChartCard({
  title,
  subtitle,
  action,
  height = 280,
  children,
}: ChartCardProps) {
  return (
    <div className="card-glass">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-white">
            {title}
          </h3>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      <div style={{ height }}>{children}</div>
    </div>
  );
}
