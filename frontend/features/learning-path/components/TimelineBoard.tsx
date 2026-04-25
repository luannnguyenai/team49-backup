import { useMemo } from "react";
import { computeRecommendedNext, groupByWeek } from "../presenters";
import { useLearningPathStore } from "../store";
import LearningUnitCard from "./cards/LearningUnitCard";

export default function TimelineBoard() {
  const items = useLearningPathStore((s) => s.items);
  const timeline = useLearningPathStore((s) => s.timeline);
  const selectItem = useLearningPathStore((s) => s.selectItem);

  const fallbackTimeline = useMemo(() => groupByWeek(items), [items]);
  const effectiveTimeline = timeline ?? fallbackTimeline;
  const recommendedId = useMemo(() => computeRecommendedNext(items), [items]);
  const allWeekNumbersMissing = items.length > 0 && items.every((item) => item.week_number == null);

  return (
    <div className="space-y-3">
      {effectiveTimeline.items.length === 1 && allWeekNumbersMissing && (
        <div className="rounded-xl border px-4 py-3 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-secondary)", backgroundColor: "var(--bg-card)" }}>
          Lộ trình hiện đang được gom vào Tuần 1; phân bổ nhiều tuần sẽ được bổ sung sau.
        </div>
      )}
      <div className="grid grid-flow-col auto-cols-[280px] gap-4 overflow-x-auto pb-4">
        {effectiveTimeline.items.map((week) => (
          <section key={week.week} className="rounded-2xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
            <div className="mb-3">
              <h3 className="font-semibold" style={{ color: "var(--text-primary)" }}>
                Tuần {week.week}
              </h3>
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                {week.total_hours}h · {week.learning_units.length} bài
              </p>
            </div>
            <div className="space-y-3">
              {week.learning_units.map((item) => (
                <LearningUnitCard
                  key={item.id}
                  item={item}
                  isRecommended={item.id === recommendedId}
                  onClick={() => selectItem(item.id)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
