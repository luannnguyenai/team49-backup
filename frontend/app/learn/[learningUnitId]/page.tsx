"use client";

// app/learn/[learningUnitId]/page.tsx
// Learning content page: markdown render, auto-TOC, reading time tracker,
// "Bắt đầu Quiz" CTA.

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  BookOpen,
  ChevronRight,
  Clock,
  ListOrdered,
  Play,
  Video,
} from "lucide-react";
import { learningUnitApi } from "@/lib/api";
import type { LearningUnitContentById } from "@/types";
import LearnMarkdown, { extractHeadings, type Heading } from "@/components/learn/LearnMarkdown";

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function readingTimeMin(markdown: string): number {
  return Math.max(1, Math.ceil(countWords(markdown) / 200));
}

function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function LearnTopicPage() {
  const { learningUnitId } = useParams<{ learningUnitId: string }>();
  const router = useRouter();

  const [content, setContent] = useState<LearningUnitContentById | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [headings, setHeadings] = useState<Heading[]>([]);
  const [activeHeading, setActiveHeading] = useState<string>("");
  const [readSeconds, setReadSeconds] = useState(0);
  const [tocOpen, setTocOpen] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const articleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!learningUnitId) return;
    setLoading(true);
    learningUnitApi
      .contentById(learningUnitId)
      .then((data) => {
        setContent(data);
        if (data.content_markdown) {
          setHeadings(extractHeadings(data.content_markdown));
        }
      })
      .catch(() => setError("Không thể tải nội dung. Vui lòng thử lại."))
      .finally(() => setLoading(false));
  }, [learningUnitId]);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setReadSeconds((s) => s + 1);
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!content?.content_markdown || headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveHeading(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: "-20% 0% -60% 0%" }
    );

    headings.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [headings, content]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Đang tải nội dung...
          </p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-medium text-red-600">{error ?? "Không tìm thấy nội dung."}</p>
          <button
            onClick={() => router.back()}
            className="mt-4 text-sm underline"
            style={{ color: "var(--text-secondary)" }}
          >
            Quay lại
          </button>
        </div>
      </div>
    );
  }

  const markdown = content.content_markdown ?? "";
  const estMinutes = markdown ? readingTimeMin(markdown) : 0;
  const readMinutes = Math.floor(readSeconds / 60);
  const readPct = estMinutes > 0 ? Math.min(100, Math.round((readMinutes / estMinutes) * 100)) : 0;

  return (
    <div className="relative flex gap-8 animate-fade-in">
      {headings.length > 0 && (
        <aside className="hidden lg:block w-56 shrink-0">
          <div className="sticky top-6 space-y-1">
            <p
              className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest"
              style={{ color: "var(--text-muted)" }}
            >
              <ListOrdered size={14} />
              Mục lục
            </p>
            {headings.map((h) => (
              <a
                key={h.id}
                href={`#${h.id}`}
                className={[
                  "block truncate rounded-md py-1 text-sm transition-colors",
                  h.level === 1 ? "pl-2 font-medium" : h.level === 2 ? "pl-4" : "pl-6",
                  activeHeading === h.id
                    ? "font-medium"
                    : "opacity-70 hover:opacity-100",
                ].join(" ")}
                style={{
                  color: activeHeading === h.id ? "var(--color-primary-600)" : "var(--text-secondary)",
                }}
                onClick={() => setActiveHeading(h.id)}
              >
                {h.text}
              </a>
            ))}
          </div>
        </aside>
      )}

      <div className="min-w-0 flex-1">
        <nav
          className="mb-4 flex items-center gap-1 text-xs"
          style={{ color: "var(--text-muted)" }}
        >
          <span>{content.section_title}</span>
          <ChevronRight size={12} />
          <span style={{ color: "var(--text-secondary)" }}>{content.title}</span>
        </nav>

        <div className="card mb-6 p-5">
          <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            {content.title}
          </h1>

          <div
            className="mt-3 flex flex-wrap items-center gap-4 text-sm"
            style={{ color: "var(--text-muted)" }}
          >
            {estMinutes > 0 && (
              <span className="flex items-center gap-1.5">
                <Clock size={14} />
                {estMinutes} phút đọc ước tính
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <BookOpen size={14} />
              Đã đọc {fmtTime(readSeconds)}
            </span>
            {content.video_url && (
              <span className="flex items-center gap-1.5">
                <Video size={14} />
                Có video
              </span>
            )}
          </div>

          {estMinutes > 0 && (
            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs" style={{ color: "var(--text-muted)" }}>
                <span>Tiến độ đọc</span>
                <span>{readPct}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                <div
                  className="h-full rounded-full bg-primary-500 transition-all duration-1000"
                  style={{ width: `${readPct}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {headings.length > 0 && (
          <div className="mb-4 lg:hidden">
            <button
              onClick={() => setTocOpen((o) => !o)}
              className="flex w-full items-center justify-between rounded-xl border px-4 py-2.5 text-sm font-medium"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <span className="flex items-center gap-2">
                <ListOrdered size={15} />
                Mục lục
              </span>
              <ChevronRight
                size={15}
                className={`transition-transform ${tocOpen ? "rotate-90" : ""}`}
              />
            </button>
            {tocOpen && (
              <div
                className="mt-1 rounded-xl border p-3"
                style={{ borderColor: "var(--border)" }}
              >
                {headings.map((h) => (
                  <a
                    key={h.id}
                    href={`#${h.id}`}
                    className="block py-1 text-sm"
                    style={{
                      paddingLeft: `${(h.level - 1) * 12 + 4}px`,
                      color: "var(--text-secondary)",
                    }}
                    onClick={() => setTocOpen(false)}
                  >
                    {h.text}
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {content.video_url && (
          <div className="card mb-6 overflow-hidden p-0">
            <video
              controls
              className="w-full"
              src={content.video_url}
            >
              Trình duyệt không hỗ trợ video.
            </video>
          </div>
        )}

        {markdown ? (
          <div
            ref={articleRef}
            className="card p-6 md:p-8"
          >
            <LearnMarkdown markdown={markdown} />
          </div>
        ) : (
          <div className="card flex min-h-40 items-center justify-center">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Nội dung đang được cập nhật.
            </p>
          </div>
        )}

        <div className="mt-8 flex items-center justify-between rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>
              Sẵn sàng kiểm tra kiến thức?
            </p>
            <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
              Làm bài quiz 10 câu để củng cố và đo lường mức độ thành thạo.
            </p>
          </div>
          <button
            onClick={() => router.push(`/quiz/${learningUnitId}`)}
            className="btn-primary flex shrink-0 items-center gap-2 ml-4"
          >
            <Play size={16} />
            Bắt đầu Quiz
          </button>
        </div>
      </div>
    </div>
  );
}
