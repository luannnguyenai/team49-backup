"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AlertCircle, RefreshCw } from "lucide-react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import LearningUnitDrawer from "./LearningUnitDrawer";
import PathRequiredState from "./PathRequiredState";
import PlannerHeader from "./PlannerHeader";
import ProfileChangeBanner from "./ProfileChangeBanner";
import TimelineBoard from "./TimelineBoard";
import { usePersistedLearnView } from "./ViewToggle";
import { useLearningPathStore } from "../store";

const RoadmapCanvas = dynamic(() => import("./RoadmapCanvas"), {
  ssr: false,
  loading: () => <CanvasSkeleton />,
});

function CanvasSkeleton() {
  return (
    <div className="h-[70vh] animate-pulse rounded-2xl border p-8" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
      <div className="mx-auto h-16 w-56 rounded-2xl bg-slate-200" />
      <div className="mx-auto mt-12 grid max-w-4xl grid-cols-2 gap-8">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="h-20 rounded-2xl bg-slate-200" />
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
          <div className="h-5 w-24 rounded bg-slate-200" />
          <div className="mt-5 space-y-3">
            {Array.from({ length: 4 }).map((__, idx) => (
              <div key={idx} className="h-20 rounded-xl bg-slate-200" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LearningPathShell() {
  const [view, setView] = usePersistedLearnView();
  const [isMobile, setIsMobile] = useState(false);
  const profile = useLearningPathStore((s) => s.profile);
  const previousProfile = useLearningPathStore((s) => s.previousProfile);
  const generatedTopologyHash = useLearningPathStore((s) => s.generatedTopologyHash);
  const items = useLearningPathStore((s) => s.items);
  const summary = useLearningPathStore((s) => s.summary);
  const loading = useLearningPathStore((s) => s.loading);
  const error = useLearningPathStore((s) => s.error);
  const loadPath = useLearningPathStore((s) => s.loadPath);
  const setProfile = useLearningPathStore((s) => s.setProfile);

  useEffect(() => {
    if (profile) {
      loadPath();
    }
  }, [loadPath, profile]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const updateIsMobile = () => setIsMobile(mediaQuery.matches);

    updateIsMobile();
    mediaQuery.addEventListener("change", updateIsMobile);

    return () => {
      mediaQuery.removeEventListener("change", updateIsMobile);
    };
  }, []);

  if (!profile) {
    return (
      <div className="mx-auto max-w-7xl animate-fade-in">
        <PathRequiredState />
      </div>
    );
  }

  if (!loading && !error && items.length === 0) {
    return (
      <div className="mx-auto max-w-7xl animate-fade-in">
        <PathRequiredState />
      </div>
    );
  }

  const shouldUseTimelineFallback = isMobile && view === "graph";

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <PlannerHeader
        profile={profile}
        summary={summary}
        view={view}
        onViewChange={setView}
        onProfileChange={setProfile}
      />
      <ProfileChangeBanner
        previousProfile={previousProfile}
        currentProfile={profile}
        generatedTopologyHash={generatedTopologyHash}
        onRefreshPath={loadPath}
        refreshing={loading}
      />

      {loading ? (
        !shouldUseTimelineFallback && view === "graph" ? <CanvasSkeleton /> : <TimelineSkeleton />
      ) : error ? (
        <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border p-8 text-center" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
          <AlertCircle className="h-10 w-10 text-red-500" />
          <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>{error}</p>
          <button type="button" onClick={loadPath} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        </div>
      ) : !shouldUseTimelineFallback && view === "graph" ? (
        <RoadmapCanvas />
      ) : (
        <div className="space-y-4">
          {shouldUseTimelineFallback ? (
            <section
              className="rounded-2xl border px-4 py-4 shadow-sm sm:px-5"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
            >
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                Graph view works best on a larger screen.
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                Weekly view keeps the planner readable and actionable on phones.
              </p>
              <button
                type="button"
                onClick={() => setView("timeline")}
                className="mt-3 inline-flex items-center rounded-full border px-3 py-2 text-sm font-semibold text-primary-600 transition hover:bg-primary-50"
                style={{ borderColor: "var(--border)" }}
              >
                Switch to weekly view
              </button>
            </section>
          ) : null}
          <TimelineBoard />
        </div>
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
