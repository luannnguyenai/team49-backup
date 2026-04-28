import type { PathItemResponse, PathStatus } from "@/types";

export function getStatusLabel(status: PathStatus): string {
  return {
    pending: "Chưa học",
    in_progress: "Đang học",
    completed: "Hoàn thành",
    skipped: "Bỏ qua",
  }[status];
}

export function getStatusIconName(status: PathStatus): "circle" | "play" | "check" | "skip" {
  const icons: Record<PathStatus, "circle" | "play" | "check" | "skip"> = {
    pending: "circle",
    in_progress: "play",
    completed: "check",
    skipped: "skip",
  };
  return icons[status];
}

export function getStatusClassName(status: PathStatus, isRecommended = false): string {
  const base = {
    pending: "border-purple-200 bg-purple-50 text-purple-900 dark:border-purple-800 dark:bg-purple-950/30 dark:text-purple-100",
    in_progress: "border-amber-400 bg-amber-50 text-amber-900 shadow-[0_0_0_3px_rgba(251,191,36,0.18)] dark:bg-amber-950/30 dark:text-amber-100",
    completed: "border-emerald-300 bg-emerald-50 text-emerald-900 opacity-70 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-100",
    skipped: "border-slate-300 bg-slate-100 text-slate-500 opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400",
  }[status];
  return isRecommended ? `${base} ring-2 ring-primary-500 ring-offset-2 ring-offset-white dark:ring-offset-slate-950` : base;
}

export function isVisibleInTimeline(item: PathItemResponse): boolean {
  return isVisibleInMainPath(item);
}

export function isIncludedInMainPath(item: PathItemResponse): boolean {
  if (item.segment_policy === "hidden") return false;
  if (item.segment_policy === "reference") return false;
  return true;
}

export function isVisibleInMainPath(item: PathItemResponse): boolean {
  if (!isIncludedInMainPath(item)) return false;
  if (item.action === "skip") return false;
  if (item.status === "skipped") return false;
  return true;
}

export function isDoneForPlannerProgress(item: PathItemResponse): boolean {
  return (
    item.status === "completed" ||
    item.status === "skipped" ||
    item.action === "skip"
  );
}

export function isOptionalIntroItem(item: PathItemResponse): boolean {
  return Boolean(
    item.section_title?.match(
      /(^|\b)(lecture|lec\.?)\s*1\s*[:-]\s*(intro|introduction)\b|^intro\b|^introduction\b/i,
    ),
  );
}
