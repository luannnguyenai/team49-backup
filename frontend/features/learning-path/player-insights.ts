import type { LearningSessionInlineQuizProgress } from "@/types";

export type PlayerInsightTone =
  | "resume"
  | "quiz_ready"
  | "active_quiz"
  | "complete"
  | "review_due"
  | "placement_lite";

export interface PlayerProgressSnapshot {
  learning_unit_id: string;
  video_progress_s?: number | null;
  watch_percent?: number | null;
  video_finished?: boolean | null;
  inline_quiz?: LearningSessionInlineQuizProgress | null;
  review_due_count?: number | null;
  mastery_stale?: boolean | null;
  has_end_quiz?: boolean | null;
}

export interface PlayerInsight {
  tone: PlayerInsightTone;
  label: string;
  hrefSuffix: string | null;
}

function checkpointCompleted(
  inlineQuiz: LearningSessionInlineQuizProgress | null | undefined,
  checkpoint: "midpoint" | "end",
): boolean {
  return Boolean(inlineQuiz?.[checkpoint]?.completed_session_id);
}

function checkpointActive(
  inlineQuiz: LearningSessionInlineQuizProgress | null | undefined,
  checkpoint: "midpoint" | "end",
): boolean {
  return Boolean(inlineQuiz?.[checkpoint]?.active_session_id);
}

function asPercent(snapshot: PlayerProgressSnapshot): number {
  return Math.max(0, Math.min(100, Math.round((snapshot.watch_percent ?? 0) * 100)));
}

export function derivePlayerInsight(snapshot: PlayerProgressSnapshot | null | undefined): PlayerInsight | null {
  if (!snapshot) return null;

  if (snapshot.mastery_stale) {
    return {
      tone: "placement_lite",
      label: "Mastery is stale, do a quick check",
      hrefSuffix: "#placement-lite",
    };
  }

  if ((snapshot.review_due_count ?? 0) > 0) {
    return {
      tone: "review_due",
      label: `Review ${snapshot.review_due_count} KPs`,
      hrefSuffix: "#review",
    };
  }

  if (checkpointActive(snapshot.inline_quiz, "end")) {
    return { tone: "active_quiz", label: "Continue end quiz", hrefSuffix: "#end-quiz" };
  }

  if (checkpointActive(snapshot.inline_quiz, "midpoint")) {
    return { tone: "active_quiz", label: "Continue mini quiz", hrefSuffix: "#midpoint-quiz" };
  }

  if (checkpointCompleted(snapshot.inline_quiz, "end")) {
    return { tone: "complete", label: "End quiz completed", hrefSuffix: null };
  }

  const videoIsDone = Boolean(snapshot.video_finished) || (snapshot.watch_percent ?? 0) >= 0.95;
  if (videoIsDone && snapshot.has_end_quiz !== false) {
    return { tone: "quiz_ready", label: "End quiz unlocked", hrefSuffix: "#end-quiz" };
  }

  if (videoIsDone) {
    return { tone: "complete", label: "Finished watching", hrefSuffix: null };
  }

  if ((snapshot.watch_percent ?? 0) > 0 || (snapshot.video_progress_s ?? 0) > 0) {
    return {
      tone: "resume",
      label: `Resume from ${asPercent(snapshot)}%`,
      hrefSuffix: null,
    };
  }

  return null;
}
