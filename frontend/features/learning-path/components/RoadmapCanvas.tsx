"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, type NodeTypes } from "reactflow";
import "reactflow/dist/style.css";

import { autoLayout } from "../lib/layout";
import { pathToFlow } from "../presenters";
import { useLearningPathStore } from "../store";
import TopicNode from "./nodes/TopicNode";
import SubtopicNode from "./nodes/SubtopicNode";

const nodeTypes: NodeTypes = {
  topic: TopicNode,
  subtopic: SubtopicNode,
};

export default function RoadmapCanvas() {
  const items = useLearningPathStore((s) => s.items);
  const selectItem = useLearningPathStore((s) => s.selectItem);
  const selectSection = useLearningPathStore((s) => s.selectSection);

  const flow = useMemo(() => {
    const model = pathToFlow(items);
    return {
      nodes: autoLayout(model.nodes, model.edges),
      edges: model.edges,
    };
  }, [items]);

  return (
    <div className="h-[70vh] overflow-hidden rounded-2xl border" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        nodeTypes={nodeTypes}
        fitView
        onlyRenderVisibleElements
        onNodeClick={(_, node) => {
          if (node.type === "topic" && node.data?.kind === "topic") {
            selectSection(node.data.sectionKey);
          }
          if (node.type === "subtopic" && node.data?.kind === "subtopic") {
            selectItem(node.data.item.id);
          }
        }}
      >
        <Background />
        <MiniMap pannable zoomable />
        <Controls />
      </ReactFlow>
    </div>
  );
}
