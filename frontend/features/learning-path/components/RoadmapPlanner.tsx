"use client";

import { useMemo } from "react";
import type { PathItemResponse } from "@/types";
import { derivePlayerInsight, type PlayerProgressSnapshot } from "../player-insights";
import { buildRoadmapModel } from "../roadmap-model";
import PathRequiredState from "./PathRequiredState";
import RoadmapConnectorLayer from "./RoadmapConnectorLayer";
import RoadmapNodeCard from "./RoadmapNodeCard";

interface RoadmapPlannerProps {
  items: PathItemResponse[];
  currentProgress?: PlayerProgressSnapshot | null;
  onSelectItem?: (id: string) => void;
  onSelectSection?: (sectionKey: string) => void;
}

export default function RoadmapPlanner({ items, currentProgress, onSelectItem, onSelectSection }: RoadmapPlannerProps) {
  const model = useMemo(() => buildRoadmapModel(items), [items]);
  const nodesById = useMemo(() => new Map(model.nodes.map((node) => [node.id, node])), [model.nodes]);

  if (model.nodes.length === 0) {
    return <PathRequiredState />;
  }

  return (
    <div
      className="relative min-h-[70vh] overflow-auto rounded-3xl border bg-slate-50 p-4 dark:bg-slate-950"
      style={{ borderColor: "var(--border)" }}
    >
      <div
        className="relative"
        style={{
          width: model.width,
          height: model.height,
          minWidth: model.width,
        }}
      >
        <RoadmapConnectorLayer connectors={model.connectors} nodesById={nodesById} />
        {model.nodes.map((node) => (
          <RoadmapNodeCard
            key={node.id}
            node={node}
            insight={
              node.kind === "unit" && node.item?.learning_unit_id === currentProgress?.learning_unit_id
                ? derivePlayerInsight(currentProgress)
                : null
            }
            onSelectItem={onSelectItem}
            onSelectSection={onSelectSection}
          />
        ))}
      </div>
    </div>
  );
}
