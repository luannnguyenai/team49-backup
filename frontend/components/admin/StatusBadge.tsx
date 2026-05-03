"use client";

// components/admin/StatusBadge.tsx

type Status = "healthy" | "degraded" | "down" | "unknown" | string;

const STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  healthy: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
    label: "Healthy",
  },
  degraded: {
    bg: "bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
    label: "Degraded",
  },
  down: {
    bg: "bg-rose-500/10",
    text: "text-rose-700 dark:text-rose-300",
    dot: "bg-rose-500",
    label: "Down",
  },
  unknown: {
    bg: "bg-slate-500/10",
    text: "text-slate-600 dark:text-slate-400",
    dot: "bg-slate-400",
    label: "Unknown",
  },
};

export default function StatusBadge({
  status,
  label,
}: {
  status: Status;
  label?: string;
}) {
  const style = STYLES[status] ?? STYLES.unknown;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${style.bg} ${style.text}`}
    >
      <span className={`h-2 w-2 rounded-full ${style.dot} animate-pulse`} />
      {label ?? style.label}
    </span>
  );
}
