import { cn } from "@/lib/utils";
import type { CourseStatus } from "@/types";

const STATUS_COPY: Record<CourseStatus, { label: string; className: string }> = {
  ready: {
    label: "Ready",
    className:
      "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  coming_soon: {
    label: "Coming soon",
    className:
      "border-amber-200 bg-amber-50 text-amber-700",
  },
  metadata_partial: {
    label: "Metadata partial",
    className:
      "border-sky-200 bg-sky-50 text-sky-700",
  },
};

export default function CourseStatusBadge({ status }: { status: CourseStatus }) {
  const copy = STATUS_COPY[status];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.16em]",
        copy.className,
      )}
    >
      {copy.label}
    </span>
  );
}
