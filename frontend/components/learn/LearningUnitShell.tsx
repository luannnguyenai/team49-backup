"use client";

// components/learn/LearningUnitShell.tsx
// Unified lecture shell with in-context AI Tutor.
// Replaces the standalone tutor page for course-first learning.

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import type { LearningUnitResponse } from "@/types";
import InContextTutor from "@/components/learn/InContextTutor";

// ── Types ──────────────────────────────────────────────────────────────────

interface Chapter {
  id: number;
  lecture_id: string;
  title: string;
  summary: string;
  start_time: number;
  end_time: number;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
  return [m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

// ── Props ───────────────────────────────────────────────────────────────────

interface LearningUnitShellProps {
  data: LearningUnitResponse;
  courseSlug: string;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function LearningUnitShell({
  data,
  courseSlug,
}: LearningUnitShellProps) {
  const { course, unit, content, tutor } = data;
  const legacyLectureId = tutor.legacy_lecture_id ?? null;

  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [tutorOpen, setTutorOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  // Load chapters from legacy lecture API if available
  useEffect(() => {
    if (!legacyLectureId) {
      setChapters([]);
      return;
    }

    api
      .get<Chapter[]>(`/api/lectures/${legacyLectureId}/toc`)
      .then((r) => setChapters(r.data))
      .catch(() => setChapters([]));
  }, [legacyLectureId]);

  // Video time tracking
  const handleTimeUpdate = () => {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  };

  // Frame capture for tutor
  const captureFrame = useCallback((): string | null => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return null;
    try {
      const c = document.createElement("canvas");
      c.width = v.videoWidth;
      c.height = v.videoHeight;
      c.getContext("2d")!.drawImage(v, 0, 0);
      return c.toDataURL("image/jpeg", 0.7).split(",")[1];
    } catch {
      return null;
    }
  }, []);

  return (
    <div
      className="h-[calc(100vh-4.5rem)] overflow-hidden rounded-[32px] border shadow-[0_18px_55px_rgba(15,23,42,0.08)]"
      style={{
        backgroundColor: "var(--bg-card)",
        borderColor: "var(--border)",
      }}
    >
      <div
        className={
          tutor.enabled && tutorOpen
            ? "flex h-full flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_22rem]"
            : "flex h-full flex-col"
        }
      >
        <div className="min-w-0 flex flex-1 flex-col overflow-hidden">
          <div
            className="flex flex-wrap items-center gap-3 border-b px-5 py-4 md:px-6"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex min-w-0 items-center gap-2 text-xs">
              <Link
                href={`/courses/${courseSlug}`}
                className="font-medium transition-colors hover:underline"
                style={{ color: "var(--text-muted)" }}
              >
                {course.title}
              </Link>
              <span style={{ color: "var(--text-muted)" }}>›</span>
              <span
                className="truncate font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {unit.title}
              </span>
            </div>

            {tutor.enabled && (
              <button
                onClick={() => setTutorOpen((o) => !o)}
                className="ml-auto inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition-all duration-200"
                style={{
                  backgroundColor: tutorOpen
                    ? "rgba(37,99,235,0.08)"
                    : "var(--bg-page)",
                  color: tutorOpen ? "#2563eb" : "var(--text-secondary)",
                  borderColor: tutorOpen
                    ? "rgba(37,99,235,0.25)"
                    : "var(--border)",
                }}
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                AI Tutor
              </button>
            )}
          </div>

          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 md:p-6">
            <div className="overflow-hidden rounded-[28px] border bg-black shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
              {content.video_url ? (
                <video
                  ref={videoRef}
                  className="aspect-video w-full cursor-pointer object-contain"
                  crossOrigin="anonymous"
                  onTimeUpdate={handleTimeUpdate}
                  onDurationChange={() => {
                    if (videoRef.current)
                      setDuration(videoRef.current.duration || 0);
                  }}
                  onClick={() => {
                    const v = videoRef.current;
                    if (v) v.paused ? v.play() : v.pause();
                  }}
                  src={content.video_url}
                />
              ) : content.body_markdown ? (
                <div className="prose prose-slate max-w-none bg-[color:var(--bg-card)] p-6 md:p-8">
                  <ReactMarkdown>{content.body_markdown}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex min-h-[24rem] items-center justify-center bg-[color:var(--bg-card)] p-6 text-center">
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    Content is being prepared for this unit.
                  </p>
                </div>
              )}
            </div>

            {content.video_url && (
              <div
                className="rounded-[24px] border px-4 py-3"
                style={{
                  backgroundColor: "var(--bg-card)",
                  borderColor: "var(--border)",
                }}
              >
                <div
                  className="relative h-1.5 cursor-pointer rounded-full"
                  style={{ backgroundColor: "var(--bg-page)" }}
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const pct = (e.clientX - rect.left) / rect.width;
                    if (videoRef.current)
                      videoRef.current.currentTime = pct * (duration || 0);
                  }}
                >
                  <div
                    className="pointer-events-none absolute left-0 top-0 h-full rounded-full"
                    style={{
                      width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%`,
                      backgroundColor: "#2563eb",
                    }}
                  />
                </div>

                <div className="mt-2 flex items-center justify-between gap-3">
                  <span
                    className="text-xs tabular-nums"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                  {chapters.length > 0 && (
                    <span
                      className="min-w-0 truncate text-xs"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {chapters.find(
                        (ch) =>
                          currentTime >= ch.start_time &&
                          currentTime < ch.end_time,
                      )?.title ?? ""}
                    </span>
                  )}
                </div>
              </div>
            )}

            {chapters.length > 0 && (
              <section
                className="rounded-[24px] border px-4 py-4 md:px-5"
                style={{
                  backgroundColor: "var(--bg-card)",
                  borderColor: "var(--border)",
                }}
              >
                <p
                  className="text-xs font-semibold uppercase tracking-[0.22em]"
                  style={{ color: "var(--text-muted)" }}
                >
                  Chapters
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {chapters.map((ch) => {
                    const isActive =
                      currentTime >= ch.start_time &&
                      currentTime < ch.end_time;
                    return (
                      <button
                        key={ch.id}
                        onClick={() => {
                          if (videoRef.current)
                            videoRef.current.currentTime = ch.start_time;
                        }}
                        className="rounded-full px-3 py-1.5 text-xs transition-colors"
                        style={{
                          backgroundColor: isActive
                            ? "rgba(37,99,235,0.1)"
                            : "var(--bg-page)",
                          color: isActive
                            ? "#2563eb"
                            : "var(--text-secondary)",
                          fontWeight: isActive ? 600 : 400,
                        }}
                      >
                        {formatTime(ch.start_time)} · {ch.title}
                      </button>
                    );
                  })}
                </div>
              </section>
            )}
          </div>
        </div>

        {tutor.enabled && tutorOpen && (
          <aside
            className="h-[24rem] shrink-0 overflow-hidden border-t lg:h-full lg:border-l lg:border-t-0"
            style={{
              borderColor: "var(--border)",
              backgroundColor: "var(--bg-card)",
            }}
          >
            <InContextTutor
              lectureId={legacyLectureId ?? ""}
              currentTime={currentTime}
              captureFrame={captureFrame}
              contextBindingId={tutor.context_binding_id ?? undefined}
              unitTitle={unit.title}
              onClose={() => setTutorOpen(false)}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
