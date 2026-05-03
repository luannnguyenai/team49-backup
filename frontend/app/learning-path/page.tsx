"use client";
// app/learning-path/page.tsx
// Learning path page showing Phase A (remediation) and Phase B (new learning) sections.

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, Lock, Play } from "lucide-react";

import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PhaseTag = "phase_a" | "phase_b" | null;
type UnitStatus = "pending" | "in_progress" | "completed";

interface PathItem {
  learning_unit_id: string;
  learning_unit_title: string;
  section_title: string;
  phase_tag: PhaseTag;
  is_locked: boolean;
  order_index: number;
  status: UnitStatus;
  estimated_hours: number | null;
}

interface LearningPathResponse {
  items: PathItem[];
  total_units: number;
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<UnitStatus, { label: string; className: string }> = {
  pending: {
    label: "Not started",
    className:
      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  },
  in_progress: {
    label: "In progress",
    className:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  completed: {
    label: "Completed",
    className:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
};

// ---------------------------------------------------------------------------
// UnitCard
// ---------------------------------------------------------------------------

function UnitCard({ item }: { item: PathItem }) {
  const badge = STATUS_BADGE[item.status];

  return (
    <div
      className="relative flex items-start justify-between gap-4 rounded-xl border p-4 transition-shadow hover:shadow-sm"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--bg-card)",
        opacity: item.is_locked ? 0.6 : 1,
      }}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2">
          {item.is_locked && (
            <span title="Complete Phase A first">
              <Lock
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-slate-400"
              />
            </span>
          )}
          <span
            className="truncate text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {item.learning_unit_title}
          </span>
        </div>

        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
          {item.section_title}
        </p>

        <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
          {item.estimated_hours != null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {Math.round(item.estimated_hours * 60)} min
            </span>
          )}
          <span className={`rounded-full px-2 py-0.5 font-medium ${badge.className}`}>
            {badge.label}
          </span>
        </div>
      </div>

      {!item.is_locked && (
        <Link
          href={`/learn/${item.learning_unit_id}`}
          className="shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
          style={{ backgroundColor: "var(--primary-600, #2563eb)" }}
        >
          <Play className="h-3 w-3" />
          Start learning
        </Link>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LearningPathPage() {
  const [items, setItems] = useState<PathItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<LearningPathResponse>("/api/learning-path")
      .then((r) => setItems(r.data.items))
      .catch(() => setError("Unable to load the learning path. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  const hasPhases = items.some((i) => i.phase_tag !== null);
  const phaseAItems = items.filter((i) => i.phase_tag === "phase_a");
  const phaseBItems = items.filter((i) => i.phase_tag === "phase_b");
  const phaseBLocked = phaseBItems.some((i) => i.is_locked);

  return (
    <div className="mx-auto max-w-3xl space-y-8 animate-fade-in py-8 px-4">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Your learning path
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Units are ordered to match your current level and progression needs.
        </p>
      </div>

      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      ) : error ? (
        <div
          className="flex h-40 items-center justify-center rounded-xl border text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          {error}
        </div>
      ) : items.length === 0 ? (
        <div
          className="flex h-40 items-center justify-center rounded-xl border text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          No learning path is available yet. Complete onboarding first.
        </div>
      ) : !hasPhases ? (
        /* Plain list when no placement data */
        <div className="space-y-3">
          {items.map((item) => (
            <UnitCard key={item.learning_unit_id} item={item} />
          ))}
        </div>
      ) : (
        /* Phase A / Phase B layout */
        <div className="space-y-8">
          {phaseAItems.length > 0 && (
            <section>
              <div className="mb-4 flex items-center gap-3">
                <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                  Phase A: Review
                </h2>
                <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
                  {phaseAItems.length} units
                </span>
              </div>
              <div className="space-y-3">
                {phaseAItems.map((item) => (
                  <UnitCard key={item.learning_unit_id} item={item} />
                ))}
              </div>
            </section>
          )}

          {phaseBItems.length > 0 && (
            <section>
              <div className="mb-4 flex items-center gap-3">
                <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                  Phase B: New learning
                </h2>
                <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  {phaseBItems.length} units
                </span>
                {phaseBLocked && (
                  <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                    <Lock className="h-3.5 w-3.5" />
                    Complete Phase A first
                  </span>
                )}
              </div>
              <div className="space-y-3">
                {phaseBItems.map((item) => (
                  <UnitCard key={item.learning_unit_id} item={item} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
