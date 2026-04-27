"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import Link from "next/link";
import {
  BookOpen,
  CheckCircle2,
  ChevronsLeft,
  ChevronsRight,
  CircleDot,
  GripVertical,
  Lightbulb,
  PlayCircle,
  Sparkles,
  X,
} from "lucide-react";

import {
  canonicalQuizApi,
  courseApi,
  learningSessionApi,
  quizApi,
} from "@/lib/api";
import type {
  CourseUnitListItem,
  InlineQuizStartPayload,
  LearningSessionInlineQuizProgress,
  LearningSessionInlineQuizState,
  LearningUnitResponse,
  QuestionForQuiz,
  QuizAnswerResponse,
  QuizCompleteResponse,
  SelectedAnswer,
} from "@/types";
import InContextTutor from "@/components/learn/InContextTutor";

interface TocSummarySection {
  section_number: number;
  timestamp: string;
  topic_title: string;
  detailed_summary: string;
  key_takeaways: string[];
}

interface TocSummaryPayload {
  lecture_title: string;
  table_of_contents: TocSummarySection[];
}

interface ChapterView {
  id: string;
  title: string;
  timestamp: string;
  start_time: number;
  end_time: number;
  key_takeaways: string[];
}

type InlineQuizCheckpointKey = "midpoint" | "end";

type InlineQuizProgress = Partial<
  Record<InlineQuizCheckpointKey, LearningSessionInlineQuizState>
>;

type InlineQuizOverlayPhase = "quiz" | "feedback" | "completing" | "result";

interface InlineQuizSessionState {
  checkpoint: InlineQuizCheckpointKey;
  sessionId: string;
  questions: QuestionForQuiz[];
  currentIndex: number;
  selectedAnswer: SelectedAnswer | null;
  feedback: QuizAnswerResponse | null;
  result: QuizCompleteResponse | null;
  phase: InlineQuizOverlayPhase;
  questionStartedAt: number;
  minimized: boolean;
}

interface LearningUnitShellProps {
  data: LearningUnitResponse;
  courseSlug: string;
}

interface VideoProgressRailMarker {
  id: string;
  label: string;
  positionPct: number;
  tone: "chapter" | "checkpoint";
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

const LEFT_PANEL_STORAGE_KEY = "learning-shell-left-panel";
const RIGHT_PANEL_STORAGE_KEY = "learning-shell-right-panel";
const LEFT_PANEL_DEFAULT_WIDTH = 288;
const RIGHT_PANEL_DEFAULT_WIDTH = 384;
const PANEL_MIN_WIDTH = 240;
const PANEL_MAX_WIDTH = 520;
const MIDPOINT_THRESHOLD = 0.5;
const END_THRESHOLD = 0.95;
const OPTION_KEYS: SelectedAnswer[] = ["A", "B", "C", "D"];
const CHECKPOINT_LABELS: Record<InlineQuizCheckpointKey, string> = {
  midpoint: "Mid-video quiz",
  end: "End-of-video quiz",
};

function formatSeconds(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const secs = safeSeconds % 60;
  if (hours > 0) {
    return [hours, minutes, secs].map((value) => String(value).padStart(2, "0")).join(":");
  }
  return [minutes, secs].map((value) => String(value).padStart(2, "0")).join(":");
}

function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(":").map((part) => Number(part));
  if (parts.some(Number.isNaN)) return 0;
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

function formatLectureLabel(orderIndex: number, fallback?: string | null) {
  return fallback?.trim() || `Lecture ${String(orderIndex).padStart(2, "0")}`;
}

function buildTutorSuggestions(unitTitle: string, activeChapter: ChapterView | null): string[] {
  const chapterTitle = activeChapter?.title ?? unitTitle;
  const firstTakeaway = activeChapter?.key_takeaways[0];

  if (firstTakeaway) {
    return [
      "Giải thích ý chính của đoạn này dễ hiểu hơn",
      `Tại sao "${chapterTitle}" lại quan trọng trong bài này?`,
    ];
  }

  return [
    `Tóm tắt nhanh phần "${chapterTitle}" cho tôi`,
    "Điểm quan trọng nhất ở đoạn này là gì?",
  ];
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function readPanelPreference(storageKey: string, defaultWidth: number) {
  if (typeof window === "undefined") {
    return { hidden: false, width: defaultWidth };
  }
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return { hidden: false, width: defaultWidth };
    const parsed = JSON.parse(raw) as { hidden?: boolean; width?: number };
    return {
      hidden: Boolean(parsed.hidden),
      width:
        typeof parsed.width === "number"
          ? clamp(parsed.width, PANEL_MIN_WIDTH, PANEL_MAX_WIDTH)
          : defaultWidth,
    };
  } catch {
    return { hidden: false, width: defaultWidth };
  }
}

function checkpointQuestionCount(checkpoint: InlineQuizCheckpointKey): number {
  return checkpoint === "midpoint" ? 3 : 5;
}

function checkpointThreshold(checkpoint: InlineQuizCheckpointKey): number {
  return checkpoint === "midpoint" ? MIDPOINT_THRESHOLD : END_THRESHOLD;
}

function toUniqueStrings(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))));
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === "string" && entry.length > 0);
}

function parseInlineQuizState(value: unknown): LearningSessionInlineQuizState {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  const candidate = value as Record<string, unknown>;
  return {
    shown: candidate.shown === true,
    active_session_id:
      typeof candidate.active_session_id === "string" ? candidate.active_session_id : null,
    completed_session_id:
      typeof candidate.completed_session_id === "string" ? candidate.completed_session_id : null,
    excluded_item_ids: asStringArray(candidate.excluded_item_ids),
    item_ids: asStringArray(candidate.item_ids),
    answered_item_ids: asStringArray(candidate.answered_item_ids),
    quiz_phase: typeof candidate.quiz_phase === "string" ? candidate.quiz_phase : null,
  };
}

function parseInlineQuizProgress(value: unknown): InlineQuizProgress {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  const candidate = value as Record<string, unknown>;
  const progress: InlineQuizProgress = {};
  if (candidate.midpoint) progress.midpoint = parseInlineQuizState(candidate.midpoint);
  if (candidate.end) progress.end = parseInlineQuizState(candidate.end);
  return progress;
}

function collectExcludedItemIds(
  checkpoint: InlineQuizCheckpointKey,
  progress: InlineQuizProgress,
): string[] {
  if (checkpoint === "midpoint") {
    return progress.midpoint?.excluded_item_ids ?? [];
  }
  return toUniqueStrings([
    ...(progress.midpoint?.excluded_item_ids ?? []),
    ...(progress.midpoint?.item_ids ?? []),
    ...(progress.end?.excluded_item_ids ?? []),
  ]);
}

function getCheckpointButtonLabel(
  checkpoint: InlineQuizCheckpointKey,
  status: "locked" | "ready" | "active" | "completed",
) {
  if (status === "active") return "Tiếp tục";
  if (status === "completed") return "Xem lại";
  if (status === "ready") return "Mở quiz";
  return `Mở ở ${Math.round(checkpointThreshold(checkpoint) * 100)}%`;
}

function getQuestionRowTone(isSelected: boolean, isCorrect: boolean | null) {
  if (isSelected && isCorrect === true) return "border-emerald-300 bg-emerald-50";
  if (isSelected && isCorrect === false) return "border-rose-300 bg-rose-50";
  if (isSelected) return "border-blue-300 bg-blue-50";
  return "border-[color:var(--border)] bg-[color:var(--bg-elevated)] hover:border-blue-200";
}

function getOptionText(question: QuestionForQuiz, option: SelectedAnswer): string {
  if (option === "A") return question.option_a;
  if (option === "B") return question.option_b;
  if (option === "C") return question.option_c;
  return question.option_d;
}

function VideoProgressRail({
  currentTime,
  duration,
  chapters,
  activeChapterTitle,
  markers,
  onSeek,
}: {
  currentTime: number;
  duration: number;
  chapters: ChapterView[];
  activeChapterTitle: string;
  markers: VideoProgressRailMarker[];
  onSeek: (seconds: number) => void;
}) {
  const progressPct = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const [hoveredSection, setHoveredSection] = useState<{
    label: string;
    positionPct: number;
  } | null>(null);

  const handleRailClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (!duration) return;
      const bounds = event.currentTarget.getBoundingClientRect();
      if (!bounds.width) return;
      const ratio = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
      onSeek(ratio * duration);
    },
    [duration, onSeek],
  );

  const updateHoveredSection = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (!duration || !chapters.length) return;
      const bounds = event.currentTarget.getBoundingClientRect();
      if (!bounds.width) return;
      const ratio = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
      const hoverTime = ratio * duration;
      const chapter =
        chapters.find(
          (candidate) =>
            hoverTime >= candidate.start_time && hoverTime < candidate.end_time,
        ) ?? chapters[chapters.length - 1];
      setHoveredSection({
        label: chapter.title,
        positionPct: ratio * 100,
      });
    },
    [chapters, duration],
  );

  return (
    <div
      className="rounded-b-3xl border-x border-b px-4 pb-4 pt-3"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          Current section: <span className="text-blue-600">{activeChapterTitle}</span>
        </p>
        <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
          {formatSeconds(currentTime)} / {formatSeconds(duration)}
        </span>
      </div>

      <div
        aria-label="Video progress rail"
        className="relative h-3 cursor-pointer rounded-full bg-slate-200/80"
        data-testid="video-progress-rail"
        onClick={handleRailClick}
        onMouseLeave={() => setHoveredSection(null)}
        onMouseMove={updateHoveredSection}
        style={{ backgroundColor: "rgba(148, 163, 184, 0.28)" }}
      >
        {hoveredSection ? (
          <div
            className="pointer-events-none absolute -top-11 z-10 -translate-x-1/2 rounded-full bg-slate-950 px-3 py-1.5 text-xs font-medium text-white shadow-lg"
            style={{ left: `${hoveredSection.positionPct}%` }}
          >
            {hoveredSection.label}
          </div>
        ) : null}

        <div
          className="absolute inset-y-0 left-0 rounded-full bg-blue-600 transition-[width] duration-150"
          style={{ width: `${progressPct}%` }}
        />

        {markers.map((marker) => (
          <button
            key={marker.id}
            aria-label={marker.label}
            className={[
              "absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 shadow-sm transition-transform",
              marker.tone === "chapter"
                ? "border-white bg-slate-900"
                : "border-white bg-amber-500",
              marker.active ? "scale-125 ring-2 ring-blue-200" : "",
              marker.disabled ? "cursor-not-allowed opacity-55" : "",
            ].join(" ")}
            data-testid={marker.tone === "chapter" ? "chapter-marker" : "checkpoint-marker"}
            disabled={marker.disabled}
            onClick={(event) => {
              event.stopPropagation();
              marker.onClick?.();
            }}
            style={{ left: `${marker.positionPct}%` }}
            title={marker.label}
            type="button"
          />
        ))}
      </div>
    </div>
  );
}

function InlineQuizOverlay({
  checkpoint,
  session,
  onStart,
  onDismiss,
  onMinimize,
  onSelectAnswer,
  onSubmitAnswer,
  onAdvance,
  onCloseResult,
}: {
  checkpoint: InlineQuizCheckpointKey;
  session: InlineQuizSessionState | null;
  onStart: () => void;
  onDismiss: () => void;
  onMinimize: () => void;
  onSelectAnswer: (answer: SelectedAnswer) => void;
  onSubmitAnswer: () => void;
  onAdvance: () => void;
  onCloseResult: () => void;
}) {
  const question = session ? session.questions[session.currentIndex] : null;
  const result = session?.result ?? null;

  return (
    <div className="pointer-events-none absolute inset-4 flex items-end justify-end">
      <div
        className="pointer-events-auto w-full max-w-md rounded-3xl border p-4 shadow-2xl backdrop-blur"
        style={{
          borderColor: "rgba(255,255,255,0.32)",
          background:
            "linear-gradient(180deg, rgba(255,251,235,0.96) 0%, rgba(239,246,255,0.98) 100%)",
          color: "#0f172a",
        }}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-amber-700">
              {CHECKPOINT_LABELS[checkpoint]}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              {session
                ? "Kiểm tra nhanh ngay trong lúc xem để khóa lại ý chính của bài."
                : `Review ${checkpointQuestionCount(checkpoint)} câu hỏi liên quan đến đoạn video hiện tại.`}
            </p>
          </div>
          <button
            aria-label="Close quiz overlay"
            className="rounded-full p-1 text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
            onClick={session?.phase === "result" ? onCloseResult : onDismiss}
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {!session && (
          <div className="space-y-3">
            <div className="rounded-2xl border border-amber-200 bg-white/72 px-4 py-3 text-sm text-slate-700">
              Quiz này sẽ chèn ngay trên video, không đẩy bạn sang màn hình khác.
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-white/80"
                onClick={onDismiss}
                type="button"
              >
                Ẩn tạm
              </button>
              <button
                className="rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 transition-transform hover:scale-[1.02]"
                onClick={onStart}
                type="button"
              >
                Bắt đầu quiz
              </button>
            </div>
          </div>
        )}

        {session && question && session.phase !== "result" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>
                Câu {session.currentIndex + 1} / {session.questions.length}
              </span>
              <button
                className="rounded-full border border-slate-200 px-3 py-1 font-medium transition-colors hover:bg-white/80"
                onClick={onMinimize}
                type="button"
              >
                Thu nhỏ
              </button>
            </div>

            <div className="rounded-2xl border border-sky-100 bg-white/82 px-4 py-4 shadow-sm">
              <p className="text-sm leading-6 text-slate-800">{question.stem_text}</p>
            </div>

            <div className="space-y-2">
              {OPTION_KEYS.map((optionKey) => {
                const optionValue = getOptionText(question, optionKey);
                const isSelected = session.selectedAnswer === optionKey;
                const isCorrect =
                  session.phase === "feedback"
                    ? session.feedback?.correct_answer === optionKey
                    : null;

                return (
                  <button
                    key={optionKey}
                    className={[
                      "flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition-colors",
                      getQuestionRowTone(isSelected, isCorrect),
                    ].join(" ")}
                    disabled={session.phase !== "quiz"}
                    onClick={() => onSelectAnswer(optionKey)}
                    type="button"
                  >
                    <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900/90 text-xs font-semibold text-white">
                      {optionKey}
                    </span>
                    <span className="text-sm leading-6 text-slate-900">{optionValue}</span>
                  </button>
                );
              })}
            </div>

            {session.phase === "feedback" && session.feedback ? (
              <div className="rounded-2xl border border-sky-100 bg-white/82 px-4 py-3 text-sm text-slate-700 shadow-sm">
                <p className="font-semibold text-amber-700">
                  {session.feedback.is_correct ? "Bạn trả lời đúng." : "Cần xem lại ý này."}
                </p>
                {session.feedback.explanation_text ? (
                  <p className="mt-1 text-slate-600">{session.feedback.explanation_text}</p>
                ) : null}
              </div>
            ) : null}

            <div className="flex items-center justify-end gap-2">
              {session.phase === "quiz" ? (
                <button
                  className="rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={session.selectedAnswer === null}
                  onClick={onSubmitAnswer}
                  type="button"
                >
                  Trả lời
                </button>
              ) : (
                <button
                  className="rounded-full bg-amber-400 px-4 py-2 text-sm font-semibold text-slate-950"
                  onClick={onAdvance}
                  type="button"
                >
                  {session.currentIndex >= session.questions.length - 1 ? "Hoàn thành quiz" : "Câu tiếp theo"}
                </button>
              )}
            </div>
          </div>
        )}

        {session?.phase === "result" && result ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-300/20 bg-emerald-400/10 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-emerald-300">
                Review completed
              </p>
              <h3 className="mt-1 text-xl font-semibold text-white">{result.score}</h3>
              <p className="mt-1 text-sm text-slate-600">
                {result.percent.toFixed(1)}% đúng trong {CHECKPOINT_LABELS[checkpoint].toLowerCase()}.
              </p>
            </div>

            <div className="flex items-center justify-between gap-3">
              <Link
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-white/80"
                href={`/history?session_id=${session.sessionId}`}
              >
                Xem lại bài đã làm
              </Link>
              <button
                className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950"
                onClick={onCloseResult}
                type="button"
              >
                Tiếp tục học
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function LearningUnitShell({ data, courseSlug }: LearningUnitShellProps) {
  const { course, unit, content, tutor } = data;
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [lectureList, setLectureList] = useState<CourseUnitListItem[]>([]);
  const [tocSummary, setTocSummary] = useState<TocSummaryPayload | null>(null);
  const [leftPanelWidth, setLeftPanelWidth] = useState(LEFT_PANEL_DEFAULT_WIDTH);
  const [rightPanelWidth, setRightPanelWidth] = useState(RIGHT_PANEL_DEFAULT_WIDTH);
  const [leftPanelHidden, setLeftPanelHidden] = useState(false);
  const [rightPanelHidden, setRightPanelHidden] = useState(false);
  const [inlineQuizProgress, setInlineQuizProgress] = useState<InlineQuizProgress>({});
  const [dismissedPrompts, setDismissedPrompts] = useState<
    Record<InlineQuizCheckpointKey, boolean>
  >({
    midpoint: false,
    end: false,
  });
  const [quizSession, setQuizSession] = useState<InlineQuizSessionState | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const resizeStateRef = useRef<{ side: "left" | "right"; startX: number; startWidth: number } | null>(
    null,
  );
  const quizProgressRef = useRef<InlineQuizProgress>({});
  const lastWatchSyncRef = useRef(0);
  const handledCheckpointHashRef = useRef<string | null>(null);

  useEffect(() => {
    quizProgressRef.current = inlineQuizProgress;
  }, [inlineQuizProgress]);

  useEffect(() => {
    const leftPref = readPanelPreference(LEFT_PANEL_STORAGE_KEY, LEFT_PANEL_DEFAULT_WIDTH);
    const rightPref = readPanelPreference(RIGHT_PANEL_STORAGE_KEY, RIGHT_PANEL_DEFAULT_WIDTH);
    setLeftPanelHidden(leftPref.hidden);
    setLeftPanelWidth(leftPref.width);
    setRightPanelHidden(rightPref.hidden);
    setRightPanelWidth(rightPref.width);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      LEFT_PANEL_STORAGE_KEY,
      JSON.stringify({ hidden: leftPanelHidden, width: leftPanelWidth }),
    );
  }, [leftPanelHidden, leftPanelWidth]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      RIGHT_PANEL_STORAGE_KEY,
      JSON.stringify({ hidden: rightPanelHidden, width: rightPanelWidth }),
    );
  }, [rightPanelHidden, rightPanelWidth]);

  useEffect(() => {
    const handlePointerMove = (event: MouseEvent) => {
      if (!resizeStateRef.current) return;
      const { side, startX, startWidth } = resizeStateRef.current;
      const delta = event.clientX - startX;
      if (side === "left") {
        setLeftPanelWidth(clamp(startWidth + delta, PANEL_MIN_WIDTH, PANEL_MAX_WIDTH));
      } else {
        setRightPanelWidth(clamp(startWidth - delta, PANEL_MIN_WIDTH, PANEL_MAX_WIDTH));
      }
    };

    const handlePointerUp = () => {
      resizeStateRef.current = null;
    };

    window.addEventListener("mousemove", handlePointerMove);
    window.addEventListener("mouseup", handlePointerUp);
    return () => {
      window.removeEventListener("mousemove", handlePointerMove);
      window.removeEventListener("mouseup", handlePointerUp);
    };
  }, []);

  useEffect(() => {
    let ignore = false;
    courseApi
      .listUnits(courseSlug)
      .then((units) => {
        if (!ignore) setLectureList(units);
      })
      .catch(() => {
        if (!ignore) setLectureList([]);
      });
    return () => {
      ignore = true;
    };
  }, [courseSlug]);

  useEffect(() => {
    if (!unit.lecture_order) {
      setTocSummary(null);
      return;
    }

    let ignore = false;
    courseApi
      .lectureToc(courseSlug, unit.lecture_order)
      .then((payload) => {
        if (!ignore) setTocSummary(payload);
      })
      .catch(() => {
        if (!ignore) setTocSummary(null);
      });

    return () => {
      ignore = true;
    };
  }, [courseSlug, unit.lecture_order]);

  useEffect(() => {
    let ignore = false;
    learningSessionApi
      .resume()
      .then((resume) => {
        if (ignore || resume.current_unit_id !== unit.id || !resume.current_progress) return;
        const progress = parseInlineQuizProgress(
          (resume.current_progress as Record<string, unknown>).inline_quiz,
        );
        setInlineQuizProgress(progress);
        quizProgressRef.current = progress;
      })
      .catch(() => {});

    return () => {
      ignore = true;
    };
  }, [unit.id]);

  const chapters = useMemo<ChapterView[]>(() => {
    if (!tocSummary?.table_of_contents?.length) return [];
    return tocSummary.table_of_contents.map((section, index, sections) => ({
      id: `${section.section_number}-${section.timestamp}`,
      title: section.topic_title,
      timestamp: section.timestamp,
      start_time: parseTimestamp(section.timestamp),
      end_time:
        index + 1 < sections.length
          ? parseTimestamp(sections[index + 1].timestamp)
          : Number.POSITIVE_INFINITY,
      key_takeaways: section.key_takeaways ?? [],
    }));
  }, [tocSummary]);

  const activeChapter = useMemo(() => {
    if (!chapters.length) return null;
    return (
      chapters.find(
        (chapter) => currentTime >= chapter.start_time && currentTime < chapter.end_time,
      ) ?? chapters[0]
    );
  }, [chapters, currentTime]);

  const watchPercent = useMemo(() => {
    if (!duration) return 0;
    return clamp(currentTime / duration, 0, 1);
  }, [currentTime, duration]);

  const tutorSuggestions = useMemo(
    () => buildTutorSuggestions(unit.lecture_title ?? unit.title, activeChapter),
    [activeChapter, unit.lecture_title, unit.title],
  );

  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d")?.drawImage(video, 0, 0);
      return canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
    } catch {
      return null;
    }
  }, []);

  const lectureHeading = unit.lecture_title ?? unit.title;

  const syncInlineQuizProgress = useCallback(
    (updater: (previous: InlineQuizProgress) => InlineQuizProgress) => {
      const next = updater(quizProgressRef.current);
      quizProgressRef.current = next;
      setInlineQuizProgress(next);
      void learningSessionApi
        .updateProgress(unit.id, {
          inline_quiz: next as LearningSessionInlineQuizProgress,
        })
        .catch(() => {});
      return next;
    },
    [unit.id],
  );

  useEffect(() => {
    if (!duration) return;
    if (Math.abs(watchPercent - lastWatchSyncRef.current) < 0.05 && watchPercent < END_THRESHOLD) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      lastWatchSyncRef.current = watchPercent;
      void learningSessionApi
        .updateProgress(unit.id, {
          video_progress_s: Math.round(currentTime),
          watch_percent: Number(watchPercent.toFixed(4)),
          video_finished: watchPercent >= END_THRESHOLD,
        })
        .catch(() => {});
    }, 450);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [currentTime, duration, unit.id, watchPercent]);

  const resumeInlineQuiz = useCallback(
    async (checkpoint: InlineQuizCheckpointKey) => {
      const checkpointState = quizProgressRef.current[checkpoint] ?? {};
      const payload: InlineQuizStartPayload = {
        learning_unit_id: unit.id,
        count: checkpointQuestionCount(checkpoint),
        source: "inline_video",
        checkpoint,
        exclude_item_ids: collectExcludedItemIds(checkpoint, quizProgressRef.current),
      };

      const response = await canonicalQuizApi.start(payload);
      const answeredCount = checkpointState.answered_item_ids?.length ?? 0;
      const itemIds = response.questions.map((question) => question.item_id);

      syncInlineQuizProgress((previous) => ({
        ...previous,
        [checkpoint]: {
          ...(previous[checkpoint] ?? {}),
          shown: true,
          active_session_id: response.session_id,
          item_ids: itemIds,
          excluded_item_ids: toUniqueStrings([
            ...collectExcludedItemIds(checkpoint, previous),
            ...itemIds,
          ]),
        },
      }));

      setDismissedPrompts((previous) => ({ ...previous, [checkpoint]: false }));
      setQuizSession({
        checkpoint,
        sessionId: response.session_id,
        questions: response.questions,
        currentIndex: Math.min(answeredCount, Math.max(response.questions.length - 1, 0)),
        selectedAnswer: null,
        feedback: null,
        result: null,
        phase: "quiz",
        questionStartedAt: Date.now(),
        minimized: false,
      });
    },
    [syncInlineQuizProgress, unit.id],
  );

  useEffect(() => {
    if (quizSession) return;
    const activeCheckpoint = (["midpoint", "end"] as InlineQuizCheckpointKey[]).find(
      (checkpoint) => Boolean(inlineQuizProgress[checkpoint]?.active_session_id),
    );
    if (!activeCheckpoint) return;
    void resumeInlineQuiz(activeCheckpoint);
  }, [inlineQuizProgress, quizSession, resumeInlineQuiz]);

  const checkpointStatus = useMemo(() => {
    return (["midpoint", "end"] as InlineQuizCheckpointKey[]).map((checkpoint) => {
      const state = inlineQuizProgress[checkpoint] ?? {};
      const threshold = checkpointThreshold(checkpoint);
      const available = watchPercent >= threshold;
      const active = Boolean(state.active_session_id);
      const completed = Boolean(state.completed_session_id);
      return {
        checkpoint,
        available,
        active,
        completed,
        threshold,
        state,
        status: completed
          ? "completed"
          : active
            ? "active"
            : available
              ? "ready"
              : "locked",
      } as const;
    });
  }, [inlineQuizProgress, watchPercent]);

  const currentPromptCheckpoint = useMemo(() => {
    if (quizSession) return null;
    for (const checkpoint of ["midpoint", "end"] as InlineQuizCheckpointKey[]) {
      const status = checkpointStatus.find((entry) => entry.checkpoint === checkpoint);
      if (!status) continue;
      if (status.active || status.completed || !status.available) continue;
      if (dismissedPrompts[checkpoint]) continue;
      return checkpoint;
    }
    return null;
  }, [checkpointStatus, dismissedPrompts, quizSession]);

  const activeQuizQuestion = quizSession ? quizSession.questions[quizSession.currentIndex] : null;

  const startCheckpointQuiz = useCallback(
    async (checkpoint: InlineQuizCheckpointKey) => {
      if (videoRef.current && !videoRef.current.paused) {
        videoRef.current.pause();
      }
      try {
        await resumeInlineQuiz(checkpoint);
      } catch {
        setDismissedPrompts((previous) => ({ ...previous, [checkpoint]: false }));
      }
    },
    [resumeInlineQuiz],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleCheckpointHash = () => {
      const hash = window.location.hash;
      const checkpoint =
        hash === "#midpoint-quiz"
          ? "midpoint"
          : hash === "#end-quiz"
            ? "end"
            : null;
      if (!checkpoint) return;
      if (handledCheckpointHashRef.current === hash) return;

      const status = checkpointStatus.find((entry) => entry.checkpoint === checkpoint);
      if (!status || status.completed || (!status.active && !status.available)) return;

      handledCheckpointHashRef.current = hash;
      void startCheckpointQuiz(checkpoint);
    };

    handleCheckpointHash();
    window.addEventListener("hashchange", handleCheckpointHash);
    return () => {
      window.removeEventListener("hashchange", handleCheckpointHash);
    };
  }, [checkpointStatus, startCheckpointQuiz]);

  const submitInlineQuizAnswer = useCallback(async () => {
    if (!quizSession || !activeQuizQuestion || quizSession.selectedAnswer === null) return;
    try {
      const feedback = await quizApi.answer(quizSession.sessionId, {
        question_id: activeQuizQuestion.id,
        selected_answer: quizSession.selectedAnswer,
        response_time_ms: Math.max(250, Date.now() - quizSession.questionStartedAt),
      });

      syncInlineQuizProgress((previous) => {
        const current = previous[quizSession.checkpoint] ?? {};
        return {
          ...previous,
          [quizSession.checkpoint]: {
            ...current,
            answered_item_ids: toUniqueStrings([
              ...(current.answered_item_ids ?? []),
              activeQuizQuestion.item_id,
            ]),
          },
        };
      });

      setQuizSession((previous) =>
        previous
          ? {
              ...previous,
              feedback,
              phase: "feedback",
            }
          : previous,
      );
    } catch {}
  }, [activeQuizQuestion, quizSession, syncInlineQuizProgress]);

  const advanceInlineQuiz = useCallback(async () => {
    if (!quizSession) return;
    const isLastQuestion = quizSession.currentIndex >= quizSession.questions.length - 1;

    if (!isLastQuestion) {
      setQuizSession((previous) =>
        previous
          ? {
              ...previous,
              currentIndex: previous.currentIndex + 1,
              selectedAnswer: null,
              feedback: null,
              phase: "quiz",
              questionStartedAt: Date.now(),
            }
          : previous,
      );
      return;
    }

    setQuizSession((previous) => (previous ? { ...previous, phase: "completing" } : previous));

    try {
      const result = await quizApi.complete(quizSession.sessionId);
      syncInlineQuizProgress((previous) => {
        const current = previous[quizSession.checkpoint] ?? {};
        return {
          ...previous,
          [quizSession.checkpoint]: {
            ...current,
            shown: true,
            active_session_id: null,
            completed_session_id: quizSession.sessionId,
            item_ids: quizSession.questions.map((question) => question.item_id),
            excluded_item_ids: toUniqueStrings([
              ...(current.excluded_item_ids ?? []),
              ...quizSession.questions.map((question) => question.item_id),
            ]),
          },
        };
      });

      setQuizSession((previous) =>
        previous
          ? {
              ...previous,
              result,
              feedback: null,
              phase: "result",
              minimized: false,
            }
          : previous,
      );
    } catch {
      setQuizSession((previous) =>
        previous
          ? {
              ...previous,
              phase: "feedback",
            }
          : previous,
      );
    }
  }, [quizSession, syncInlineQuizProgress]);

  const handleSeek = useCallback((seconds: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = seconds;
    setCurrentTime(seconds);
  }, []);

  const chapterMarkers = useMemo<VideoProgressRailMarker[]>(() => {
    if (!duration) return [];
    return chapters.map((chapter) => ({
      id: chapter.id,
      label: chapter.title,
      positionPct: clamp((chapter.start_time / duration) * 100, 0, 100),
      tone: "chapter",
      active: activeChapter?.id === chapter.id,
      onClick: () => handleSeek(chapter.start_time),
    }));
  }, [activeChapter?.id, chapters, duration, handleSeek]);

  const checkpointMarkers = useMemo<VideoProgressRailMarker[]>(() => {
    return checkpointStatus.map((status) => ({
      id: `${status.checkpoint}-checkpoint`,
      label: CHECKPOINT_LABELS[status.checkpoint],
      positionPct: status.threshold * 100,
      tone: "checkpoint",
      active: quizSession?.checkpoint === status.checkpoint,
      disabled: !status.available && !status.active,
      onClick: () => {
        if (status.active || status.available) {
          void startCheckpointQuiz(status.checkpoint);
        }
      },
    }));
  }, [checkpointStatus, quizSession?.checkpoint, startCheckpointQuiz]);

  const allRailMarkers = useMemo(
    () => [...chapterMarkers, ...checkpointMarkers],
    [chapterMarkers, checkpointMarkers],
  );

  const gridTemplateColumns = useMemo(() => {
    const leftWidth = leftPanelHidden ? "0px" : `${leftPanelWidth}px`;
    const leftHandle = leftPanelHidden ? "0px" : "12px";
    const rightHandle = rightPanelHidden ? "0px" : "12px";
    const rightWidth = rightPanelHidden ? "0px" : `${rightPanelWidth}px`;
    return `${leftWidth} ${leftHandle} minmax(0,1fr) ${rightHandle} ${rightWidth}`;
  }, [leftPanelHidden, leftPanelWidth, rightPanelHidden, rightPanelWidth]);

  return (
    <div
      className="h-[calc(100vh-4.5rem)] overflow-hidden rounded-card-lg border shadow-card"
      style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex h-full flex-col">
        <div
          className="flex items-center gap-2 border-b px-5 py-4 text-xs md:px-6"
          style={{ borderColor: "var(--border)" }}
        >
          <Link
            href={`/courses/${courseSlug}`}
            className="font-medium transition-colors hover:underline"
            style={{ color: "var(--text-muted)" }}
          >
            {course.title}
          </Link>
          <span style={{ color: "var(--text-muted)" }}>›</span>
          <span className="truncate font-semibold" style={{ color: "var(--text-primary)" }}>
            {lectureHeading}
          </span>
        </div>

        <div
          className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[var(--learning-shell-grid)]"
          style={{ ["--learning-shell-grid" as string]: gridTemplateColumns }}
        >
          <aside
            className={[
              "hidden min-h-0 overflow-hidden border-r md:flex md:flex-col",
              leftPanelHidden ? "pointer-events-none opacity-0" : "",
            ].join(" ")}
            style={{
              borderColor: "var(--border)",
              backgroundColor: "var(--bg-sidebar, var(--bg-card))",
            }}
          >
            <div className="flex items-center justify-between gap-3 border-b px-5 py-4" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs font-semibold uppercase tracking-widest-sm" style={{ color: "var(--text-muted)" }}>
                Bài học
              </p>
              <button
                aria-label="Hide lessons panel"
                className="rounded-full p-1.5 transition-colors hover:bg-slate-100"
                onClick={() => setLeftPanelHidden(true)}
                type="button"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-3">
              {lectureList.map((lecture) => {
                const isActive =
                  lecture.order_index === unit.lecture_order || lecture.slug === unit.slug;
                return (
                  <Link
                    key={`${lecture.order_index}-${lecture.slug}`}
                    href={`/courses/${courseSlug}/learn/${lecture.slug}`}
                    className="mb-2 block rounded-2xl border px-4 py-3 transition-colors"
                    style={{
                      borderColor: isActive ? "rgba(37,99,235,0.28)" : "var(--border)",
                      backgroundColor: isActive ? "rgba(37,99,235,0.08)" : "transparent",
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-[11px] font-semibold uppercase tracking-widest-sm text-blue-600">
                        {formatLectureLabel(lecture.order_index, lecture.lecture_label)}
                      </p>
                      {lecture.is_completed ? (
                        <span
                          aria-label={`${formatLectureLabel(
                            lecture.order_index,
                            lecture.lecture_label,
                          )} completed`}
                          className="text-emerald-500"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {lecture.title}
                    </p>
                  </Link>
                );
              })}
            </div>
          </aside>

          <div
            aria-label="Resize lessons panel"
            className={[
              "relative hidden cursor-col-resize items-center justify-center md:flex",
              leftPanelHidden ? "pointer-events-none opacity-0" : "",
            ].join(" ")}
            data-testid="left-panel-resize-handle"
            onMouseDown={(event) => {
              resizeStateRef.current = {
                side: "left",
                startX: event.clientX,
                startWidth: leftPanelWidth,
              };
            }}
          >
            <div className="flex h-16 w-3 items-center justify-center rounded-full bg-slate-100 text-slate-400">
              <GripVertical className="h-4 w-4" />
            </div>
          </div>

          <main className="relative min-h-0 overflow-y-auto p-5 md:p-6">
            {leftPanelHidden ? (
              <button
                aria-label="Open lessons panel"
                className="absolute left-0 top-6 z-20 hidden -translate-x-1/2 rounded-full border bg-white px-3 py-2 shadow-md md:inline-flex"
                onClick={() => setLeftPanelHidden(false)}
                type="button"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            ) : null}

            {rightPanelHidden && tutor.enabled ? (
              <button
                aria-label="Open AI Tutor panel"
                className="absolute right-0 top-6 z-20 hidden translate-x-1/2 rounded-full border bg-white px-3 py-2 shadow-md md:inline-flex"
                onClick={() => setRightPanelHidden(false)}
                type="button"
              >
                <Sparkles className="h-4 w-4 text-blue-600" />
              </button>
            ) : null}

            <div className="relative">
              <section
                className="overflow-hidden rounded-t-3xl border border-b-0 shadow-card"
                style={{
                  background:
                    "radial-gradient(circle at top, rgba(59,130,246,0.16), rgba(15,23,42,0.94) 58%)",
                }}
              >
                {content.video_url ? (
                  <video
                    ref={videoRef}
                    className="aspect-video w-full object-contain"
                    crossOrigin="anonymous"
                    src={content.video_url}
                    onTimeUpdate={() => {
                      if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
                    }}
                    onDurationChange={() => {
                      if (videoRef.current) setDuration(videoRef.current.duration || 0);
                    }}
                    onEnded={() => {
                      const video = videoRef.current;
                      if (!video) return;
                      const finalDuration = video.duration || duration || 0;
                      if (finalDuration > 0) {
                        setDuration(finalDuration);
                        setCurrentTime(finalDuration);
                      }
                    }}
                    controls
                  />
                ) : (
                  <div className="flex min-h-[24rem] items-center justify-center bg-[color:var(--bg-card)] p-6 text-center">
                    <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                      Video is not available for this lecture yet.
                    </p>
                  </div>
                )}
              </section>

              <VideoProgressRail
                currentTime={currentTime}
                duration={duration}
                chapters={chapters}
                activeChapterTitle={activeChapter?.title ?? "No section available"}
                markers={allRailMarkers}
                onSeek={handleSeek}
              />

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {checkpointStatus.map((entry) => {
                  const canOpen = entry.status === "ready" || entry.status === "active";
                  const historyHref = entry.state.completed_session_id
                    ? `/history?session_id=${entry.state.completed_session_id}`
                    : null;
                  return (
                    <div
                      key={entry.checkpoint}
                      className="flex items-center justify-between gap-3 rounded-2xl border px-4 py-3"
                      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-elevated)" }}
                    >
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-widest-sm text-amber-600">
                          {CHECKPOINT_LABELS[entry.checkpoint]}
                        </p>
                        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                          {entry.status === "completed"
                            ? "Đã hoàn thành review cho checkpoint này."
                            : entry.status === "active"
                              ? "Bạn đang có một quiz dở dang ở checkpoint này."
                              : entry.status === "ready"
                                ? "Checkpoint đã mở. Bạn có thể làm quiz ngay bây giờ."
                                : `Checkpoint sẽ mở sau khi xem ${Math.round(entry.threshold * 100)}% video.`}
                        </p>
                      </div>

                      {entry.status === "completed" && historyHref ? (
                        <Link
                          className="inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium"
                          href={historyHref}
                        >
                          <PlayCircle className="h-4 w-4" />
                          {getCheckpointButtonLabel(entry.checkpoint, entry.status)}
                        </Link>
                      ) : (
                        <button
                          className="inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={!canOpen}
                          onClick={() => void startCheckpointQuiz(entry.checkpoint)}
                          type="button"
                        >
                          <CircleDot className="h-4 w-4" />
                          {getCheckpointButtonLabel(entry.checkpoint, entry.status)}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              {currentPromptCheckpoint ? (
                <InlineQuizOverlay
                  checkpoint={currentPromptCheckpoint}
                  onAdvance={advanceInlineQuiz}
                  onCloseResult={() => setQuizSession(null)}
                  onDismiss={() => {
                    const checkpoint = currentPromptCheckpoint;
                    setDismissedPrompts((previous) => ({ ...previous, [checkpoint]: true }));
                    syncInlineQuizProgress((previous) => ({
                      ...previous,
                      [checkpoint]: {
                        ...(previous[checkpoint] ?? {}),
                        shown: true,
                      },
                    }));
                  }}
                  onMinimize={() => {}}
                  onSelectAnswer={() => {}}
                  onStart={() => void startCheckpointQuiz(currentPromptCheckpoint)}
                  onSubmitAnswer={submitInlineQuizAnswer}
                  session={null}
                />
              ) : null}

              {quizSession && !quizSession.minimized ? (
                <InlineQuizOverlay
                  checkpoint={quizSession.checkpoint}
                  onAdvance={advanceInlineQuiz}
                  onCloseResult={() => {
                    setQuizSession(null);
                    if (videoRef.current) {
                      void videoRef.current.play().catch(() => {});
                    }
                  }}
                  onDismiss={() => setQuizSession((previous) => (previous ? { ...previous, minimized: true } : previous))}
                  onMinimize={() => setQuizSession((previous) => (previous ? { ...previous, minimized: true } : previous))}
                  onSelectAnswer={(answer) =>
                    setQuizSession((previous) =>
                      previous
                        ? {
                            ...previous,
                            selectedAnswer: answer,
                          }
                        : previous,
                    )
                  }
                  onStart={() => {}}
                  onSubmitAnswer={submitInlineQuizAnswer}
                  session={quizSession}
                />
              ) : null}

              {quizSession?.minimized ? (
                <button
                  className="absolute bottom-4 right-4 z-20 inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/88 px-4 py-2 text-sm font-medium text-slate-800 shadow-lg backdrop-blur"
                  onClick={() => setQuizSession((previous) => (previous ? { ...previous, minimized: false } : previous))}
                  type="button"
                >
                  <Sparkles className="h-4 w-4 text-amber-300" />
                  Tiếp tục {CHECKPOINT_LABELS[quizSession.checkpoint].toLowerCase()}
                </button>
              ) : null}

              {!quizSession && dismissedPrompts.midpoint && checkpointStatus[0]?.status === "ready" ? (
                <button
                  className="absolute bottom-4 right-4 z-20 inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/88 px-4 py-2 text-sm font-medium text-slate-800 shadow-lg backdrop-blur"
                  onClick={() => {
                    setDismissedPrompts((previous) => ({ ...previous, midpoint: false }));
                  }}
                  type="button"
                >
                  <Sparkles className="h-4 w-4 text-amber-300" />
                  Mở lại mid-video quiz
                </button>
              ) : null}
            </div>

            {activeChapter && activeChapter.key_takeaways.length > 0 && (
              <section className="mt-6 rounded-card border px-5 py-5" style={{ borderColor: "var(--border)" }}>
                <div className="mb-4 flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-100 text-amber-500 shadow-sm">
                    <Lightbulb className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-widest-sm text-amber-600">
                      IDEA
                    </p>
                    <h2 className="mt-1 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                      Key ideas at this moment
                    </h2>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                      {activeChapter.title}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {activeChapter.key_takeaways.map((takeaway) => (
                    <div
                      key={takeaway}
                      className="flex items-start gap-3 rounded-2xl border border-amber-200/70 bg-amber-50/70 px-4 py-3"
                    >
                      <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                      <p className="text-sm leading-6" style={{ color: "var(--text-primary)" }}>
                        {takeaway}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {chapters.length > 0 && (
              <section className="mt-6 rounded-card border px-5 py-5" style={{ borderColor: "var(--border)" }}>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-widest-sm text-blue-600">
                      Timestamps
                    </p>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                      Chuyển nhanh theo từng phần của video
                    </p>
                  </div>
                  <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
                    {formatSeconds(currentTime)} / {formatSeconds(duration)}
                  </span>
                </div>

                <div className="space-y-2">
                  {chapters.map((chapter) => {
                    const isActive = activeChapter?.id === chapter.id;
                    return (
                      <button
                        key={chapter.id}
                        type="button"
                        onClick={() => handleSeek(chapter.start_time)}
                        className="flex w-full items-start gap-4 rounded-2xl border px-4 py-3 text-left transition-colors"
                        style={{
                          borderColor: isActive ? "rgba(37,99,235,0.28)" : "var(--border)",
                          backgroundColor: isActive ? "rgba(37,99,235,0.08)" : "transparent",
                        }}
                      >
                        <span className="shrink-0 font-mono text-sm text-blue-600">
                          {chapter.timestamp}
                        </span>
                        <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                          {chapter.title}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
            )}
          </main>

          <div
            aria-label="Resize AI Tutor panel"
            className={[
              "relative hidden cursor-col-resize items-center justify-center md:flex",
              rightPanelHidden || !tutor.enabled ? "pointer-events-none opacity-0" : "",
            ].join(" ")}
            data-testid="right-panel-resize-handle"
            onMouseDown={(event) => {
              resizeStateRef.current = {
                side: "right",
                startX: event.clientX,
                startWidth: rightPanelWidth,
              };
            }}
          >
            <div className="flex h-16 w-3 items-center justify-center rounded-full bg-slate-100 text-slate-400">
              <GripVertical className="h-4 w-4" />
            </div>
          </div>

          <aside
            className={[
              "hidden min-h-0 overflow-hidden border-l md:flex",
              rightPanelHidden || !tutor.enabled ? "pointer-events-none opacity-0" : "",
            ].join(" ")}
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
          >
            {tutor.enabled ? (
              <div className="min-h-0 flex-1">
                <InContextTutor
                  lectureId={tutor.legacy_lecture_id ?? ""}
                  currentTime={currentTime}
                  captureFrame={captureFrame}
                  contextBindingId={tutor.context_binding_id ?? undefined}
                  onClose={() => setRightPanelHidden(true)}
                  suggestions={tutorSuggestions}
                  unitTitle={lectureHeading}
                />
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
