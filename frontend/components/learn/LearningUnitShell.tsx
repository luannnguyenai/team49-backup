"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { BookOpen, Lightbulb } from "lucide-react";

import { courseApi } from "@/lib/api";
import type { CourseUnitListItem, LearningUnitResponse } from "@/types";
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

interface LearningUnitShellProps {
  data: LearningUnitResponse;
  courseSlug: string;
}

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

function courseFolderFromSlug(courseSlug: string): string {
  if (courseSlug === "cs231n") return "CS231n";
  if (courseSlug === "cs224n") return "CS224n";
  return courseSlug;
}

function buildTocSummaryPath(courseSlug: string, lectureOrder: number | null | undefined): string | null {
  if (!lectureOrder) return null;
  return `/data/courses/${courseFolderFromSlug(courseSlug)}/ToC_Summary/lecture-${lectureOrder}.json`;
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

export default function LearningUnitShell({ data, courseSlug }: LearningUnitShellProps) {
  const { course, unit, content, tutor } = data;
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [lectureList, setLectureList] = useState<CourseUnitListItem[]>([]);
  const [tocSummary, setTocSummary] = useState<TocSummaryPayload | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let ignore = false;
    courseApi.listUnits(courseSlug).then((units) => {
      if (!ignore) setLectureList(units);
    }).catch(() => {
      if (!ignore) setLectureList([]);
    });
    return () => {
      ignore = true;
    };
  }, [courseSlug]);

  useEffect(() => {
    const tocPath = buildTocSummaryPath(courseSlug, unit.lecture_order);
    if (!tocPath) {
      setTocSummary(null);
      return;
    }

    let ignore = false;
    fetch(tocPath)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load ToC summary (${response.status})`);
        }
        return response.json() as Promise<TocSummaryPayload>;
      })
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

        <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[18rem_minmax(0,1fr)_24rem]">
          <aside
            className="hidden min-h-0 border-r md:flex md:flex-col"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-sidebar, var(--bg-card))" }}
          >
            <div className="border-b px-5 py-4" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs font-semibold uppercase tracking-widest-sm" style={{ color: "var(--text-muted)" }}>
                Bài học
              </p>
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
                    <p className="text-[11px] font-semibold uppercase tracking-widest-sm text-blue-600">
                      {formatLectureLabel(lecture.order_index, lecture.lecture_label)}
                    </p>
                    <p className="mt-1 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {lecture.title}
                    </p>
                  </Link>
                );
              })}
            </div>
          </aside>

          <main className="min-h-0 overflow-y-auto p-5 md:p-6">
            <section className="overflow-hidden rounded-card border bg-black shadow-card">
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
                        onClick={() => {
                          if (videoRef.current) videoRef.current.currentTime = chapter.start_time;
                          setCurrentTime(chapter.start_time);
                        }}
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
          </main>

          <aside
            className="hidden min-h-0 border-l md:flex"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
          >
            {tutor.enabled ? (
              <div className="min-h-0 flex-1">
                <InContextTutor
                  lectureId={tutor.legacy_lecture_id ?? ""}
                  currentTime={currentTime}
                  captureFrame={captureFrame}
                  contextBindingId={tutor.context_binding_id ?? undefined}
                  unitTitle={lectureHeading}
                  suggestions={tutorSuggestions}
                />
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
