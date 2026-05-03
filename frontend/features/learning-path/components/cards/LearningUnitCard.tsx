import { CheckCircle2, Circle, PlayCircle, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PathItemResponse } from "@/types";
import { formatDurationFromHours } from "../../lib/duration";
import { getStatusClassName, getStatusLabel } from "../../lib/status";

function StatusIcon({ status }: { status: PathItemResponse["status"] }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "in_progress") return <PlayCircle className="h-4 w-4" />;
  if (status === "skipped") return <SkipForward className="h-4 w-4" />;
  return <Circle className="h-4 w-4" />;
}

export default function LearningUnitCard({
  item,
  isRecommended,
  onClick,
}: {
  item: PathItemResponse;
  isRecommended: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-xl border p-3 text-left transition-transform hover:-translate-y-0.5",
        getStatusClassName(item.status, isRecommended),
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className={cn("line-clamp-2 text-sm font-semibold", item.status === "completed" || item.status === "skipped" ? "line-through" : "")}>
          {item.learning_unit_title}
        </p>
        <StatusIcon status={item.status} />
      </div>
      <p className="mt-1 line-clamp-1 text-xs opacity-80">{item.section_title ?? "Other"}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span>{getStatusLabel(item.status)}</span>
        {item.estimated_hours != null && <span>{formatDurationFromHours(item.estimated_hours)}</span>}
        {isRecommended && <span className="rounded-full bg-primary-600 px-2 py-0.5 text-white">Next up</span>}
      </div>
    </button>
  );
}
