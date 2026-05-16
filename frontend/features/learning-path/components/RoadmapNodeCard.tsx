"use client";

import { CheckCircle2, Circle, PlayCircle, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlayerInsight } from "../player-insights";
import { describePlannerReason } from "../planner-reasons";
import { getStatusLabel } from "../lib/status";
import type { RoadmapNodeModel } from "../roadmap-model";
import PlayerInsightBadge from "./PlayerInsightBadge";

interface RoadmapNodeCardProps {
  node: RoadmapNodeModel;
  insight?: PlayerInsight | null;
  onSelectItem?: (id: string) => void;
  onSelectSection?: (sectionKey: string) => void;
}

function statusIcon(status: RoadmapNodeModel["status"]) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "in_progress") return <PlayCircle className="h-4 w-4" />;
  if (status === "skipped") return <SkipForward className="h-4 w-4" />;
  return <Circle className="h-4 w-4" />;
}

function statusLabel(status: RoadmapNodeModel["status"]): string {
  if (status === "topic") return "Section";
  return getStatusLabel(status);
}

export default function RoadmapNodeCard({ node, insight, onSelectItem, onSelectSection }: RoadmapNodeCardProps) {
  if (node.kind === "course") {
    return (
      <div
        className="pointer-events-none absolute z-0 rounded-[28px] border border-blue-100 bg-white/80 shadow-sm ring-1 ring-blue-50"
        style={{
          left: node.x,
          top: node.y,
          width: node.width,
          height: node.height,
        }}
      >
        <div className="px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
            Course
          </p>
          <p className="mt-1 text-lg font-bold text-slate-950">{node.title}</p>
          {node.subtitle ? (
            <p className="mt-1 text-sm text-slate-500">{node.subtitle}</p>
          ) : null}
        </div>
      </div>
    );
  }

  const isTopic = node.kind === "topic";
  const label = isTopic ? `${node.title} ${node.subtitle ?? ""}` : `${node.title} ${statusLabel(node.status)}`;

  const handleClick = () => {
    if (isTopic && node.sectionKey) {
      onSelectSection?.(node.sectionKey);
      return;
    }
    if (node.itemId) {
      onSelectItem?.(node.itemId);
    }
  };

  return (
    <button
      type="button"
      aria-label={label}
      onClick={handleClick}
      className={cn(
        "absolute z-20 rounded-2xl border text-left shadow-sm transition focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-white",
        isTopic
          ? "bg-yellow-300 px-5 py-4 text-slate-950 hover:bg-yellow-200"
          : "bg-white px-5 py-4 hover:-translate-y-0.5 hover:shadow-md",
        node.isRecommended && "ring-2 ring-amber-400 ring-offset-2 ring-offset-white",
        node.status === "completed" && "opacity-75",
        node.status === "skipped" && "opacity-55",
      )}
      style={{
        left: node.x,
        top: node.y,
        width: node.width,
        height: node.height,
        borderColor: isTopic ? "#111827" : "var(--border)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className={cn("line-clamp-2 font-semibold leading-snug", isTopic ? "text-base" : "text-sm")} style={!isTopic ? { color: "var(--text-primary)" } : undefined}>
            {node.title}
          </p>
          {node.subtitle ? (
            <p className="mt-1 line-clamp-1 text-xs" style={!isTopic ? { color: "var(--text-secondary)" } : undefined}>
              {node.subtitle}
            </p>
          ) : null}
        </div>
        {!isTopic ? (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600">
            {statusIcon(node.status)}
            {statusLabel(node.status)}
          </span>
        ) : null}
      </div>
      {!isTopic && node.isRecommended ? (
        <span className="mt-2 inline-flex rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-800">
          Recommended next
        </span>
      ) : null}
      {!isTopic && insight ? <PlayerInsightBadge insight={insight} /> : null}
      {!isTopic && node.item?.reason_codes?.length ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {node.item.reason_codes.slice(0, 3).map((code) => {
            const reason = describePlannerReason(code);
            return (
              <span
                key={code}
                title={reason.details}
                className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700"
              >
                {reason.label}
              </span>
            );
          })}
        </div>
      ) : null}
    </button>
  );
}
