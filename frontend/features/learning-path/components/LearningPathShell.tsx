"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { AlertCircle, RefreshCw } from "lucide-react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "./EmptyState";
import LearningUnitDrawer from "./LearningUnitDrawer";
import TimelineBoard from "./TimelineBoard";
import ViewToggle, { usePersistedLearnView } from "./ViewToggle";
import { useLearningPathStore } from "../store";

const RoadmapCanvas = dynamic(() => import("./RoadmapCanvas"), {
  ssr: false,
  loading: () => <CanvasSkeleton />,
});

function CanvasSkeleton() {
  return (
    <div className="h-[70vh] animate-pulse rounded-2xl border p-8" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
      <div className="mx-auto h-16 w-56 rounded-2xl bg-slate-200 dark:bg-slate-800" />
      <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-8">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="h-20 rounded-2xl bg-slate-200 dark:bg-slate-800" />
        ))}
      </div>
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="grid grid-flow-col auto-cols-[280px] gap-4 overflow-hidden pb-4">
      {Array.from({ length: 3 }).map((_, col) => (
        <div key={col} className="h-96 animate-pulse rounded-2xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
          <div className="h-5 w-24 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="mt-5 space-y-3">
            {Array.from({ length: 4 }).map((__, idx) => (
              <div key={idx} className="h-20 rounded-xl bg-slate-200 dark:bg-slate-800" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LearningPathShell() {
  const [view, setView] = usePersistedLearnView();
  const items = useLearningPathStore((s) => s.items);
  const summary = useLearningPathStore((s) => s.summary);
  const loading = useLearningPathStore((s) => s.loading);
  const error = useLearningPathStore((s) => s.error);
  const loadPath = useLearningPathStore((s) => s.loadPath);

  useEffect(() => {
    loadPath();
  }, [loadPath]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Lộ trình của bạn
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            Xem lộ trình cá nhân hóa dưới dạng đồ thị hoặc theo tuần.
          </p>
          {summary && (
            <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
              {summary.completed_units}/{summary.total_units} bài hoàn thành · {summary.in_progress_units} bài đang học
            </p>
          )}
        </div>
        <ViewToggle view={view} onChange={setView} />
      </div>

      {loading ? (
        view === "graph" ? <CanvasSkeleton /> : <TimelineSkeleton />
      ) : error ? (
        <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border p-8 text-center" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
          <AlertCircle className="h-10 w-10 text-red-500" />
          <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>{error}</p>
          <button type="button" onClick={loadPath} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">
            <RefreshCw className="h-4 w-4" /> Thử lại
          </button>
        </div>
      ) : items.length === 0 ? (
        <EmptyState />
      ) : view === "graph" ? (
        <RoadmapCanvas />
      ) : (
        <TimelineBoard />
      )}

      {loading && (
        <div className="sr-only">
          <LoadingSpinner size="sm" />
        </div>
      )}
      <LearningUnitDrawer />
    </div>
  );
}
