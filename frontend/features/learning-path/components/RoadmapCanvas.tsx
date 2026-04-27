"use client";

import { useLearningPathStore } from "../store";
import PathRequiredState from "./PathRequiredState";
import RoadmapPlanner from "./RoadmapPlanner";

export default function RoadmapCanvas() {
  const profile = useLearningPathStore((s) => s.profile);
  const items = useLearningPathStore((s) => s.items);
  const currentProgress = useLearningPathStore((s) => s.currentProgress);
  const selectItem = useLearningPathStore((s) => s.selectItem);
  const selectSection = useLearningPathStore((s) => s.selectSection);

  if (!profile || items.length === 0) {
    return <PathRequiredState />;
  }

  return (
    <RoadmapPlanner
      items={items}
      currentProgress={currentProgress}
      onSelectItem={selectItem}
      onSelectSection={selectSection}
    />
  );
}
