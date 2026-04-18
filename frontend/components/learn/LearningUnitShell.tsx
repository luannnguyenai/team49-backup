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

  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [tutorOpen, setTutorOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  // Load chapters from legacy lecture API if available
  useEffect(() => {
    // Extract legacy lecture ID from the unit context binding
    // The binding ID format is "ctx_unit_lecture_XX"
    const unitId = unit.id; // e.g. "unit_lecture_01"
    const lectureNum = unitId.replace("unit_lecture_", "");
    const legacyLectureId = `cs231n_lecture_${lectureNum}`;

    api
      .get<Chapter[]>(`/api/lectures/${legacyLectureId}/toc`)
      .then((r) => setChapters(r.data))
      .catch(() => setChapters([]));
  }, [unit.id]);

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

  // Get legacy lecture ID for the tutor
  const getLegacyLectureId = () => {
    const lectureNum = unit.id.replace("unit_lecture_", "");
    return `cs231n_lecture_${lectureNum}`;
  };

  return (
    <div
      className="flex h-[calc(100vh-4.5rem)] overflow-hidden"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* ═══════════════════════════════════════════════════════════════
          MAIN AREA — Video + Course Info
      ═══════════════════════════════════════════════════════════════ */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Breadcrumb bar */}
        <div
          className="flex h-12 items-center gap-2 border-b px-4 shrink-0"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          <Link
            href={`/courses/${courseSlug}`}
            className="text-xs font-medium transition-colors hover:underline"
            style={{ color: "var(--text-muted)" }}
          >
            {course.title}
          </Link>
          <span style={{ color: "var(--text-muted)" }}>›</span>
          <span
            className="text-xs font-semibold truncate"
            style={{ color: "var(--text-primary)" }}
          >
            {unit.title}
          </span>

          {/* AI Tutor toggle */}
          {tutor.enabled && (
            <button
              onClick={() => setTutorOpen((o) => !o)}
              className="ml-auto flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold transition-all duration-200"
              style={{
                backgroundColor: tutorOpen
                  ? "rgba(37,99,235,0.1)"
                  : "var(--bg-page)",
                color: tutorOpen ? "#2563eb" : "var(--text-secondary)",
                border: `1px solid ${tutorOpen ? "rgba(37,99,235,0.3)" : "var(--border)"}`,
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

        {/* Video player */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {content.video_url ? (
            <>
              <div className="w-full aspect-video bg-black shrink-0">
                <video
                  ref={videoRef}
                  className="w-full h-full object-contain cursor-pointer"
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
              </div>

              {/* Progress bar */}
              <div
                className="px-3 py-2 shrink-0"
                style={{
                  backgroundColor: "var(--bg-card)",
                  borderTop: "1px solid var(--border)",
                }}
              >
                <div
                  className="relative h-1.5 rounded-full cursor-pointer"
                  style={{ backgroundColor: "var(--bg-page)" }}
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const pct = (e.clientX - rect.left) / rect.width;
                    if (videoRef.current)
                      videoRef.current.currentTime = pct * (duration || 0);
                  }}
                >
                  <div
                    className="absolute left-0 top-0 h-full rounded-full pointer-events-none"
                    style={{
                      width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%`,
                      backgroundColor: "#2563eb",
                    }}
                  />
                </div>
                <div className="flex items-center justify-between mt-1.5">
                  <span
                    className="text-xs tabular-nums"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                  {chapters.length > 0 && (
                    <span
                      className="text-xs truncate"
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
            </>
          ) : (
            // No video — show markdown content or placeholder
            <div className="flex-1 p-6 overflow-y-auto">
              {content.body_markdown ? (
                <div className="prose prose-slate max-w-3xl mx-auto">
                  <ReactMarkdown>{content.body_markdown}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-center justify-center min-h-[40vh]">
                  <p
                    className="text-sm"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Content is being prepared for this unit.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Chapter list below video */}
          {chapters.length > 0 && (
            <div
              className="border-t px-4 py-3 shrink-0"
              style={{
                borderColor: "var(--border)",
                backgroundColor: "var(--bg-card)",
              }}
            >
              <p
                className="text-xs font-semibold uppercase tracking-wider mb-2"
                style={{ color: "var(--text-muted)" }}
              >
                Chapters
              </p>
              <div className="flex flex-wrap gap-2">
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
                      className="rounded-lg px-3 py-1.5 text-xs transition-colors"
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
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          RIGHT PANEL — In-Context AI Tutor
      ═══════════════════════════════════════════════════════════════ */}
      {tutor.enabled && tutorOpen && (
        <aside
          className="flex flex-col border-l shrink-0 w-[22rem] overflow-hidden"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          <InContextTutor
            lectureId={getLegacyLectureId()}
            currentTime={currentTime}
            captureFrame={captureFrame}
            contextBindingId={tutor.context_binding_id ?? undefined}
            unitTitle={unit.title}
            onClose={() => setTutorOpen(false)}
          />
        </aside>
      )}
    </div>
  );
}
