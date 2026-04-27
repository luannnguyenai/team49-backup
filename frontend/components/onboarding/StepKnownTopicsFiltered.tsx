"use client";
// Step 3 — experienced users rate DB-backed topic clusters instead of raw units.

import { useEffect, useMemo, useState } from "react";
import { Check, Eye, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { canonicalSectionApi } from "@/lib/api";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { CourseSectionDetail, LearningUnitSelectionItem } from "@/types";

const GOAL_COURSE_MAP: Record<string, string[] | undefined> = {
  computer_vision: ["cs230", "cs231n"],
  nlp: ["cs230", "cs224n"],
};

const COURSE_LABELS: Record<string, string> = {
  cs230: "Deep Learning foundation",
  cs231n: "Computer Vision",
  cs224n: "Natural Language Processing",
};

type ClusterLevel = "not_started" | "reviewed" | "confident";

interface Cluster {
  id: string;
  courseId: string;
  title: string;
  units: LearningUnitSelectionItem[];
}

interface Props {
  onNext: () => void;
  onBack: () => void;
  onSkipAll: () => void;
}

function representativeUnitIds(units: LearningUnitSelectionItem[], level: ClusterLevel): string[] {
  if (level === "not_started") return [];
  const limit = level === "confident" ? 4 : 2;
  return units.slice(0, limit).map((unit) => unit.id);
}

function clusterLevelFromSelection(cluster: Cluster, selectedSet: Set<string>): ClusterLevel {
  const selectedCount = cluster.units.filter((unit) => selectedSet.has(unit.id)).length;
  if (selectedCount >= Math.min(cluster.units.length, 4)) return "confident";
  if (selectedCount > 0) return "reviewed";
  return "not_started";
}

function levelLabel(level: ClusterLevel): string {
  if (level === "confident") return "Tự tin";
  if (level === "reviewed") return "Đã học qua";
  return "Chưa học";
}

export default function StepKnownTopicsFiltered({ onNext, onBack, onSkipAll }: Props) {
  const goalIds = useOnboardingStore((s) => s.goalIds);
  const knownUnitIds = useOnboardingStore((s) => s.knownUnitIds);
  const setKnownUnitIds = useOnboardingStore((s) => s.setKnownUnitIds);

  const [allSections, setAllSections] = useState<CourseSectionDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedClusterId, setExpandedClusterId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const list = await canonicalSectionApi.list();
        const details = await Promise.all(
          list.map((section) => canonicalSectionApi.detail(section.id)),
        );
        setAllSections(details);
      } catch {
        setError("Không thể tải dữ liệu. Vui lòng thử lại.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const clusters = useMemo<Cluster[]>(() => {
    const selectedCourseIds = new Set(
      goalIds.flatMap((goalId) => GOAL_COURSE_MAP[goalId] ?? []),
    );

    return allSections
      .filter((section) => {
        const courseId = section.canonical_course_id?.toLowerCase();
        return courseId ? selectedCourseIds.has(courseId) : false;
      })
      .sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0))
      .map((section) => ({
        id: section.id,
        courseId: section.canonical_course_id?.toLowerCase() ?? "unknown",
        title: section.title,
        units: [...section.learning_units].sort(
          (a, b) => (a.order_index ?? 0) - (b.order_index ?? 0),
        ),
      }))
      .filter((cluster) => cluster.units.length > 0);
  }, [allSections, goalIds]);

  const selectedSet = useMemo(() => new Set(knownUnitIds), [knownUnitIds]);
  const selectedProbeCount = knownUnitIds.length;

  function setClusterLevel(cluster: Cluster, level: ClusterLevel) {
    const clusterUnitIds = new Set(cluster.units.map((unit) => unit.id));
    const next = knownUnitIds.filter((unitId) => !clusterUnitIds.has(unitId));
    setKnownUnitIds([...next, ...representativeUnitIds(cluster.units, level)]);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm" style={{ color: "var(--text-muted)" }}>
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Bạn đã học qua cụm nào?
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Chọn mức tự đánh giá cho từng cụm. Hệ thống chỉ dùng lựa chọn này để lấy một số câu hỏi placement phù hợp.
        </p>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {clusters.length === 0 ? (
        <div className="rounded-xl border p-4 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          Chưa có cụm nội dung cho lộ trình này.
        </div>
      ) : (
        <div className="space-y-3">
          {clusters.map((cluster) => {
            const currentLevel = clusterLevelFromSelection(cluster, selectedSet);
            const isExpanded = expandedClusterId === cluster.id;

            return (
              <div
                key={cluster.id}
                className="rounded-xl border-2 p-4"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {cluster.title}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      {COURSE_LABELS[cluster.courseId] ?? cluster.courseId} · {cluster.units.length} unit
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedClusterId(isExpanded ? null : cluster.id)}
                    className="rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors hover:bg-slate-50 dark:hover:bg-slate-800"
                    style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
                    aria-label={`Xem nhanh ${cluster.title}`}
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                </div>

                {isExpanded && (
                  <div
                    className="mt-3 rounded-lg border p-3"
                    style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}
                  >
                    <p className="mb-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                      Nội dung đại diện
                    </p>
                    <ul className="space-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      {cluster.units.slice(0, 5).map((unit) => (
                        <li key={unit.id}>- {unit.title}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="mt-4 grid grid-cols-3 gap-2">
                  {(["not_started", "reviewed", "confident"] as const).map((level) => {
                    const isSelected = currentLevel === level;
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setClusterLevel(cluster, level)}
                        className={cn(
                          "flex items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-xs font-semibold transition-all",
                          isSelected
                            ? "border-primary-600 bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300"
                            : "hover:border-slate-300",
                        )}
                        style={{ borderColor: isSelected ? undefined : "var(--border)" }}
                      >
                        {isSelected && <Check className="h-3 w-3" />}
                        {levelLabel(level)}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedProbeCount > 0 && (
        <p className="text-xs font-medium text-primary-600">
          Đã chọn {selectedProbeCount} unit đại diện để placement kiểm chứng.
        </p>
      )}

      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Quay lại
        </button>
        <button
          type="button"
          onClick={onSkipAll}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Bỏ qua
        </button>
        <button
          type="button"
          onClick={onNext}
          className="ml-auto rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Tiếp tục
        </button>
      </div>
    </div>
  );
}
