import { BookOpen } from "lucide-react";
import type { NodeProps } from "reactflow";
import type { TopicNodeData } from "../../presenters";

export default function TopicNode({ data }: NodeProps<TopicNodeData>) {
  return (
    <button
      type="button"
      className="min-w-56 rounded-2xl border-2 border-dashed border-amber-500 bg-amber-100 px-4 py-3 text-left shadow-[3px_3px_0_0_rgba(0,0,0,0.12)] transition-transform hover:-translate-y-0.5 dark:bg-amber-950/40"
      aria-label={`Mở nhóm ${data.title}`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-200 text-amber-800 dark:bg-amber-900 dark:text-amber-100">
          <BookOpen className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-bold leading-snug" style={{ color: "var(--text-primary)" }}>
            {data.title}
          </p>
          <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
            {data.count} bài học
          </p>
        </div>
      </div>
    </button>
  );
}
