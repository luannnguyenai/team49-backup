"use client";

import { useMemo, useState } from "react";
import { Check, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOnboardingStore } from "@/stores/onboardingStore";
import {
  selectRepresentativeUnitIds,
  type PriorCandidateTopic,
  type PriorTopicLevel,
} from "./priorCandidateBuilder";

interface Props {
  topics: PriorCandidateTopic[];
  analysisFallback?: boolean;
  modelLabel?: string | null;
  onNext: () => void;
  onBack: () => void;
  onSkipAll: () => void;
}

function levelLabel(level: PriorTopicLevel): string {
  if (level === "confident") return "Tự tin";
  if (level === "reviewed") return "Đã học qua";
  return "Chưa học";
}

function topicLabel(topic: PriorCandidateTopic): string {
  return topic.aiDisplayLabel?.trim() || topic.displayLabel;
}

function levelButtonAria(level: PriorTopicLevel, topic: PriorCandidateTopic): string {
  return `${levelLabel(level)} ${topicLabel(topic)}`;
}

function topicLevelFromSelection(topic: PriorCandidateTopic, selectedSet: Set<string>): PriorTopicLevel {
  const selectedCount = topic.units.filter((unit) => selectedSet.has(unit.id)).length;
  if (selectedCount >= Math.min(topic.units.length, 4)) return "confident";
  if (selectedCount > 0) return "reviewed";
  return "not_started";
}

function topicSummary(topic: PriorCandidateTopic): string | null {
  return topic.summary?.trim() || null;
}

export default function StepKnownTopicsFiltered({
  topics,
  analysisFallback = false,
  modelLabel = null,
  onNext,
  onBack,
  onSkipAll,
}: Props) {
  const knownUnitIds = useOnboardingStore((s) => s.knownUnitIds);
  const setKnownUnitIds = useOnboardingStore((s) => s.setKnownUnitIds);
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);

  const selectedSet = useMemo(() => new Set(knownUnitIds), [knownUnitIds]);
  const visibleTopics = useMemo(
    () => topics.filter((topic) => topic.suggestedLevel !== "confident"),
    [topics],
  );
  const hiddenConfidentCount = topics.length - visibleTopics.length;

  function setTopicLevel(topic: PriorCandidateTopic, level: PriorTopicLevel) {
    const topicUnitIds = new Set(topic.units.map((unit) => unit.id));
    const next = knownUnitIds.filter((unitId) => !topicUnitIds.has(unitId));
    setKnownUnitIds([...next, ...selectRepresentativeUnitIds(topic, level)]);
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Xác nhận các cụm AI gợi ý
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          AI đã tự chọn các cụm khớp rõ với mô tả của bạn. Chỉ những cụm chưa chắc mới hiện ra
          để bạn quyết định thêm; đây vẫn chưa được tính là mastery.
        </p>
      </div>

      <div
        className="rounded-xl border p-4 text-xs leading-relaxed"
        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
      >
        {analysisFallback
          ? "AI chưa trả kết quả hợp lệ, đang dùng shortlist fallback từ nội dung bạn nhập."
          : `Shortlist được tạo bởi ${modelLabel ?? "AI reasoning model"}.`}
      </div>

      {hiddenConfidentCount > 0 && (
        <div
          className="rounded-xl border border-primary-100 bg-primary-50 p-3 text-xs font-medium text-primary-700 dark:border-primary-900/40 dark:bg-primary-900/20 dark:text-primary-300"
        >
          {hiddenConfidentCount} cụm khớp rõ với mô tả của bạn đã được chọn ẩn để placement kiểm chứng.
        </div>
      )}

      {visibleTopics.length === 0 ? (
        <div
          className="rounded-xl border p-4 text-sm"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          Không có cụm nào cần hỏi thêm. Bạn có thể tiếp tục để hệ thống tạo placement phù hợp.
        </div>
      ) : (
        <div className="space-y-3">
          {visibleTopics.map((topic) => {
            const currentLevel = topicLevelFromSelection(topic, selectedSet);
            const isExpanded = expandedTopicId === topic.id;
            const summary = topicSummary(topic);
            const label = topicLabel(topic);

            return (
              <div
                key={topic.id}
                className="rounded-xl border-2 p-4"
                style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                      {label}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      {topic.units.length} unit đại diện để placement kiểm chứng
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setExpandedTopicId(isExpanded ? null : topic.id)}
                    className="rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors hover:bg-slate-50 dark:hover:bg-slate-800"
                    style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
                    aria-label={`Xem nhanh ${label}`}
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
                    {summary ? (
                      <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                        {summary}
                      </p>
                    ) : (
                      <ul className="space-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
                        {topic.units.slice(0, 5).map((unit) => (
                          <li key={unit.id}>- {unit.title}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                <div className="mt-4 grid grid-cols-3 gap-2">
                  {(["not_started", "reviewed", "confident"] as const).map((level) => {
                    const isSelected = currentLevel === level;
                    return (
                      <button
                        key={level}
                        type="button"
                        aria-label={levelButtonAria(level, topic)}
                        onClick={() => setTopicLevel(topic, level)}
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

      {knownUnitIds.length > 0 && (
        <p className="text-xs font-medium text-primary-600">
          Đã chọn {knownUnitIds.length} unit đại diện để placement kiểm chứng.
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
