"use client";

import { ReactNode } from "react";

type Cols = 2 | 3 | 4 | 5;

type Props = {
  title: string;
  description?: string;
  cols?: Cols;
  children: ReactNode;
};

const COLS_CLASS: Record<Cols, string> = {
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
  5: "lg:grid-cols-5",
};

export default function KpiGroup({ title, description, cols = 4, children }: Props) {
  return (
    <section className="space-y-3">
      <header className="flex items-baseline justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {title}
        </h3>
        {description && (
          <p className="text-[11px] text-slate-400">{description}</p>
        )}
      </header>
      <div className={`grid grid-cols-1 gap-3 sm:grid-cols-2 ${COLS_CLASS[cols]}`}>
        {children}
      </div>
    </section>
  );
}
