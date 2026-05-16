"use client";

import { AlertTriangle, CheckCircle2, PlayCircle, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlayerInsight } from "../player-insights";

interface PlayerInsightBadgeProps {
  insight: PlayerInsight;
}

function iconForTone(tone: PlayerInsight["tone"]) {
  if (tone === "complete") return <CheckCircle2 className="h-3.5 w-3.5" />;
  if (tone === "placement_lite") return <AlertTriangle className="h-3.5 w-3.5" />;
  if (tone === "review_due") return <RotateCcw className="h-3.5 w-3.5" />;
  if (tone === "quiz_ready" || tone === "active_quiz") return <Sparkles className="h-3.5 w-3.5" />;
  return <PlayCircle className="h-3.5 w-3.5" />;
}

export default function PlayerInsightBadge({ insight }: PlayerInsightBadgeProps) {
  return (
    <span
      className={cn(
        "mt-2 inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-semibold",
        insight.tone === "complete" && "bg-emerald-100 text-emerald-800",
        insight.tone === "placement_lite" && "bg-red-100 text-red-800",
        insight.tone === "review_due" && "bg-blue-100 text-blue-800",
        (insight.tone === "quiz_ready" || insight.tone === "active_quiz") && "bg-amber-100 text-amber-800",
        insight.tone === "resume" && "bg-slate-100 text-slate-700",
      )}
    >
      {iconForTone(insight.tone)}
      {insight.label}
    </span>
  );
}
