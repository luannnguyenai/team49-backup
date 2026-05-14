import { describe, expect, it } from "vitest";

import {
  applyAgentActivityStatus,
  applyAgentActivityThought,
  completeAgentActivity,
  createAgentActivity,
  formatAgentActivityDuration,
  getAgentActivityHeader,
} from "@/features/agent/lib/activity";

describe("agent activity timeline", () => {
  it("formats active and completed activity durations", () => {
    expect(formatAgentActivityDuration(12_200)).toBe("12s");
    expect(formatAgentActivityDuration(65_000)).toBe("1m 05s");

    expect(getAgentActivityHeader({ elapsedMs: 12_200, completed: false })).toBe("Thinking · 12s");
    expect(getAgentActivityHeader({ elapsedMs: 12_200, completed: true })).toBe("Thought for 12s");
  });

  it("builds a readable course-search activity timeline", () => {
    let activity = createAgentActivity({
      message: "Find CNN pruning",
      startedAt: 1_000,
    });

    activity = applyAgentActivityThought(activity, {
      user_goal: "Find CNN pruning",
      active_topic: "CNN pruning",
      evidence_need: "course_sources",
      tool_plan: ["search_course_content", "read_sources", "compose_answer"],
    });
    activity = applyAgentActivityStatus(activity, "Searching course content");
    activity = applyAgentActivityStatus(activity, "Reading sources");
    activity = applyAgentActivityStatus(activity, "Composing answer");
    activity = completeAgentActivity(activity, {
      completedAt: 13_200,
      citationCount: 3,
    });

    expect(activity.completedAt).toBe(13_200);
    expect(activity.steps).toEqual([
      {
        id: "understanding",
        title: "Understanding your question",
        detail: "Topic: CNN pruning",
      },
      {
        id: "searching",
        title: "Searching course content",
        detail: 'Query: "CNN pruning"',
      },
      {
        id: "reading",
        title: "Reading sources",
        detail: "Using available source evidence",
      },
      {
        id: "composing",
        title: "Composing answer",
        detail: "Grounding response with 3 citations",
      },
    ]);
  });
});
