import { describe, expect, it } from "vitest";
import { derivePlayerInsight, type PlayerProgressSnapshot } from "@/features/learning-path/player-insights";

function snapshot(overrides: Partial<PlayerProgressSnapshot>): PlayerProgressSnapshot {
  return {
    learning_unit_id: "unit-a",
    ...overrides,
  };
}

describe("derivePlayerInsight", () => {
  it("prioritizes stale mastery placement-lite", () => {
    expect(derivePlayerInsight(snapshot({ mastery_stale: true }))).toMatchObject({
      tone: "placement_lite",
      hrefSuffix: "#placement-lite",
    });
  });

  it("shows active checkpoint quiz links before resume", () => {
    expect(
      derivePlayerInsight(
        snapshot({
          watch_percent: 0.7,
          inline_quiz: {
            midpoint: { active_session_id: "quiz-1" },
          },
        }),
      ),
    ).toMatchObject({
      tone: "active_quiz",
      hrefSuffix: "#midpoint-quiz",
    });
  });

  it("does not mark end quiz complete just because the video is finished", () => {
    expect(
      derivePlayerInsight(
        snapshot({
          video_finished: true,
          inline_quiz: {},
          has_end_quiz: true,
        }),
      ),
    ).toMatchObject({
      tone: "quiz_ready",
      label: "End quiz đã mở",
      hrefSuffix: "#end-quiz",
    });
  });

  it("marks complete only after end checkpoint completion", () => {
    expect(
      derivePlayerInsight(
        snapshot({
          video_finished: true,
          inline_quiz: {
            end: { completed_session_id: "quiz-end" },
          },
        }),
      ),
    ).toMatchObject({
      tone: "complete",
      hrefSuffix: null,
    });
  });
});
