import { CheckCircle2, Circle, PlayCircle, SkipForward } from "lucide-react";
import type { NodeProps } from "reactflow";
import { cn } from "@/lib/utils";
import { getStatusClassName, getStatusLabel } from "../../lib/status";
import type { SubtopicNodeData } from "../../presenters";

function StatusIcon({ status }: { status: SubtopicNodeData["item"]["status"] }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "in_progress") return <PlayCircle className="h-4 w-4" />;
  if (status === "skipped") return <SkipForward className="h-4 w-4" />;
  return <Circle className="h-4 w-4" />;
}

export default function SubtopicNode({ data }: NodeProps<SubtopicNodeData>) {
  const { item, isRecommended } = data;
  return (
    <button
      type="button"
      className={cn(
        "w-64 rounded-2xl border-2 px-4 py-3 text-left shadow-sm transition-transform hover:-translate-y-0.5",
        getStatusClassName(item.status, isRecommended),
      )}
      aria-label={`Mở bài ${item.learning_unit_title}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className={cn("line-clamp-2 text-sm font-semibold leading-snug", item.status === "completed" || item.status === "skipped" ? "line-through" : "")}>
          {item.learning_unit_title}
        </p>
        <span className="shrink-0" aria-hidden="true">
          <StatusIcon status={item.status} />
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-white/70 px-2 py-0.5 dark:bg-slate-950/40">
          {getStatusLabel(item.status)}
        </span>
        {item.estimated_hours != null && (
          <span className="rounded-full bg-white/70 px-2 py-0.5 dark:bg-slate-950/40">
            {item.estimated_hours}h
          </span>
        )}
        {isRecommended && (
          <span className="rounded-full bg-primary-600 px-2 py-0.5 text-white">Tiếp theo</span>
        )}
      </div>
    </button>
  );
}
