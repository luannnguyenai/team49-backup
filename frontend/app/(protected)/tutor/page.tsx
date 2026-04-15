"use client";

import { useState, useEffect, useRef, useCallback, type RefObject, type MouseEvent as ReactMouseEvent } from "react";
import { api } from "@/lib/api";
import {
  Send,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  FileText,
  AlignLeft,
  ToggleLeft,
  ToggleRight,
  Sparkles,
  Zap,
  BookOpen,
  MessageSquare,
  Bot,
  PlayCircle,
  Clock,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface Lecture {
  id: string;
  title: string;
  description: string | null;
  video_url: string | null;
  duration: number | null;
}

interface Chapter {
  id: number;
  lecture_id: string;
  title: string;
  summary: string;
  start_time: number;
  end_time: number;
}

interface ChatMessage {
  id?: number;
  role: "user" | "ai" | "error";
  content: string;
  rating?: number | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
  return [m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

// ── Page ──────────────────────────────────────────────────────────────────────

type RightTab = "lesson" | "transcript" | "copilot";

// ── Custom Video Controls with YouTube-style chapter markers ──────────────────
function VideoControls({
  videoRef,
  currentTime,
  duration,
  chapters,
  onSeek,
}: {
  videoRef: RefObject<HTMLVideoElement>;
  currentTime: number;
  duration: number;
  chapters: Chapter[];
  onSeek: (t: number) => void;
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [hoveredChapter, setHoveredChapter] = useState<string | null>(null);
  const [hoverPct, setHoverPct] = useState(0);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    v.addEventListener("play", onPlay);
    v.addEventListener("pause", onPause);
    return () => {
      v.removeEventListener("play", onPlay);
      v.removeEventListener("pause", onPause);
    };
  }, [videoRef]);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play(); else v.pause();
  };

  const handleProgressClick = (e: ReactMouseEvent<HTMLDivElement>) => {
    const rect = progressRef.current?.getBoundingClientRect();
    if (!rect || !duration) return;
    const pct = (e.clientX - rect.left) / rect.width;
    onSeek(Math.max(0, Math.min(pct * duration, duration)));
  };

  const handleProgressHover = (e: ReactMouseEvent<HTMLDivElement>) => {
    const rect = progressRef.current?.getBoundingClientRect();
    if (!rect || !duration) return;
    const pct = Math.max(0, Math.min((e.clientX - rect.left) / rect.width, 1));
    setHoverPct(pct * 100);
    const t = pct * duration;
    setHoveredChapter(
      chapters.find((c) => t >= c.start_time && t < c.end_time)?.title ?? null
    );
  };

  const playedPct = duration > 0 ? (currentTime / duration) * 100 : 0;
  const activeTitle = chapters.find(
    (ch) => currentTime >= ch.start_time && currentTime < ch.end_time
  )?.title ?? "";

  return (
    <div
      className="px-3 py-2 space-y-1.5 shrink-0"
      style={{ backgroundColor: "var(--bg-card)", borderTop: "1px solid var(--border)" }}
    >
      {/* Seekbar + chapter markers */}
      <div className="relative pt-2">
        <div
          ref={progressRef}
          className="relative h-1.5 rounded-full cursor-pointer"
          style={{ backgroundColor: "var(--bg-page)" }}
          onClick={handleProgressClick}
          onMouseMove={handleProgressHover}
          onMouseLeave={() => setHoveredChapter(null)}
        >
          {/* Played fill */}
          <div
            className="absolute left-0 top-0 h-full rounded-full pointer-events-none"
            style={{ width: `${playedPct}%`, backgroundColor: "#2563eb" }}
          />
          {/* Chapter markers */}
          {chapters.map((ch) => {
            const pct = duration > 0 ? (ch.start_time / duration) * 100 : 0;
            if (pct <= 0.5 || pct >= 99.5) return null;
            return (
              <div
                key={ch.id}
                className="absolute w-2 h-2 rounded-full bg-white ring-1 ring-blue-400 pointer-events-none"
                style={{ left: `${pct}%`, top: "50%", transform: "translate(-50%,-50%)" }}
              />
            );
          })}
          {/* Hover tooltip */}
          {hoveredChapter && (
            <div
              className="absolute bottom-5 px-2 py-1 rounded text-xs text-white pointer-events-none whitespace-nowrap z-10"
              style={{
                left: `${hoverPct}%`,
                transform: "translateX(-50%)",
                backgroundColor: "rgba(0,0,0,0.85)",
              }}
            >
              {hoveredChapter}
            </div>
          )}
        </div>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-3">
        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          className="shrink-0 transition-opacity hover:opacity-70"
          style={{ color: "var(--text-primary)" }}
        >
          {isPlaying ? (
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          )}
        </button>

        {/* Time display */}
        <span className="text-xs tabular-nums shrink-0" style={{ color: "var(--text-muted)" }}>
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {/* Active chapter name */}
        <span className="text-xs flex-1 truncate" style={{ color: "var(--text-secondary)" }}>
          {activeTitle}
        </span>

        {/* Volume */}
        <input
          type="range" min={0} max={1} step={0.05} value={volume}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            setVolume(v);
            if (videoRef.current) videoRef.current.volume = v;
          }}
          className="w-16 h-1 shrink-0 cursor-pointer accent-blue-600"
        />

        {/* Fullscreen */}
        <button
          onClick={() => videoRef.current?.requestFullscreen?.()}
          className="shrink-0 transition-opacity hover:opacity-70"
          style={{ color: "var(--text-muted)" }}
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default function TutorPage() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [selectedLecture, setSelectedLecture] = useState<string>("");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [quizEnabled, setQuizEnabled] = useState(false);
  const [rightTab, setRightTab] = useState<RightTab>("transcript");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [chaptersOpen, setChaptersOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Session / progress ────────────────────────────────────────────────────
  const sessionId = useRef(
    typeof window !== "undefined"
      ? localStorage.getItem("al_tutor_session") ??
        (() => {
          const id = crypto.randomUUID();
          localStorage.setItem("al_tutor_session", id);
          return id;
        })()
      : "ssr"
  );

  const saveProgress = useCallback(() => {
    if (!selectedLecture || !videoRef.current || videoRef.current.currentTime < 1) return;
    api.post("/api/progress", {
      session_id: sessionId.current,
      lecture_id: selectedLecture,
      last_timestamp: videoRef.current.currentTime,
    }).catch(() => {});
  }, [selectedLecture]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (videoRef.current && !videoRef.current.paused) saveProgress();
    }, 10_000);
    return () => clearInterval(interval);
  }, [saveProgress]);

  // ── Load lectures ─────────────────────────────────────────────────────────
  useEffect(() => {
    api.get<Lecture[]>("/api/lectures").then((r) => {
      setLectures(r.data);
      if (r.data.length > 0) setSelectedLecture(r.data[0].id);
    }).catch(() => {});
  }, []);

  // ── Load chapters + restore progress ─────────────────────────────────────
  useEffect(() => {
    if (!selectedLecture) return;
    api.get<Chapter[]>(`/api/lectures/${selectedLecture}/toc`).then((r) => {
      setChapters(r.data);
    }).catch(() => setChapters([]));

    api.get<Record<string, number>>(`/api/progress/${sessionId.current}`).then((r) => {
      const ts = r.data[selectedLecture];
      if (ts && ts > 1 && videoRef.current) videoRef.current.currentTime = ts;
    }).catch(() => {});
  }, [selectedLecture]);

  // ── Auto-scroll chat ──────────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Video time update ─────────────────────────────────────────────────────
  const handleTimeUpdate = () => {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  };

  // ── Capture frame ─────────────────────────────────────────────────────────
  const captureFrame = (): string | null => {
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
  };

  // ── Rate answer ───────────────────────────────────────────────────────────
  const rateAnswer = async (msgIdx: number, qaId: number, rating: number) => {
    try {
      await api.post(`/api/history/${qaId}/rate`, { rating });
      setMessages((prev) =>
        prev.map((m, i) => (i === msgIdx ? { ...m, rating } : m))
      );
    } catch {}
  };

  // ── Send message ──────────────────────────────────────────────────────────
  const handleSend = useCallback(async (textOverride?: string) => {
    const q = (textOverride ?? input).trim();
    if (!q || streaming || !selectedLecture) return;

    // Switch to copilot tab so user sees the response
    setRightTab("copilot");
    setInput("");
    setStreaming(true);
    const img = captureFrame();

    const userMsg: ChatMessage = { role: "user", content: q };
    const aiPlaceholder: ChatMessage = { role: "ai", content: "" };

    setMessages((prev) => {
      const next = [...prev, userMsg, aiPlaceholder];
      return next;
    });

    // aiIdx = messages.length + 1 after adding userMsg
    const aiIdx = messages.length + 1;

    try {
      const resp = await fetch(
        "/api/lectures/ask",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lecture_id: selectedLecture,
            current_timestamp: currentTime,
            question: q,
            image_base64: img,
          }),
        }
      );

      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      let qaId: number | undefined;

      let hasError = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done || hasError) break;
        const text = decoder.decode(value);
        for (const line of text.split("\n")) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line.trim());
            if (data.e) {
              setMessages((prev) =>
                prev.map((m, i) => i === aiIdx ? { ...m, role: "error", content: data.e } : m)
              );
              hasError = true;
              break;
            }
            if (data.status) {
              setMessages((prev) =>
                prev.map((m, i) => i === aiIdx ? { ...m, content: fullText || data.status } : m)
              );
            }
            if (data.a) {
              fullText += data.a;
              setMessages((prev) =>
                prev.map((m, i) => i === aiIdx ? { ...m, content: fullText } : m)
              );
            }
            if (data.qa_id) qaId = data.qa_id;
          } catch {}
        }
      }

      if (qaId) {
        setMessages((prev) =>
          prev.map((m, i) => (i === aiIdx ? { ...m, id: qaId } : m))
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection error";
      setMessages((prev) =>
        prev.map((m, i) => i === aiIdx ? { ...m, role: "error", content: msg } : m)
      );
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }, [input, streaming, selectedLecture, messages.length, currentTime]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Derived ───────────────────────────────────────────────────────────────
  const lecture = lectures.find((l) => l.id === selectedLecture);
  const hasMessages = messages.length > 0;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="flex h-[calc(100vh-4.5rem)] overflow-hidden -mx-4 -mt-4 md:-mx-6 md:-mt-6"
      style={{ backgroundColor: "var(--bg-page)" }}
    >

      {/* ═══════════════════════════════════════════════════════════════════
          LEFT PANEL — Course content (lecture list)
      ═══════════════════════════════════════════════════════════════════ */}
      <aside
        className="flex flex-col border-r shrink-0 transition-all duration-300 overflow-hidden"
        style={{
          width: leftCollapsed ? "3rem" : "18rem",
          borderColor: "var(--border)",
          backgroundColor: "var(--bg-card)",
        }}
      >
        {/* Header */}
        <div
          className="flex h-12 items-center justify-between border-b px-3 shrink-0"
          style={{ borderColor: "var(--border)" }}
        >
          {!leftCollapsed && (
            <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              Nội dung khóa học
            </span>
          )}
          <button
            onClick={() => setLeftCollapsed((c) => !c)}
            className="ml-auto rounded-lg p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0"
            style={{ color: "var(--text-muted)" }}
          >
            {leftCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {!leftCollapsed && (
          <div className="flex flex-col flex-1 overflow-y-auto">
            {/* Course stats */}
            {lecture && (
              <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs leading-relaxed line-clamp-2 mb-2" style={{ color: "var(--text-secondary)" }}>
                  {lecture.description ?? "Khóa học video bài giảng"}
                </p>
                {/* Progress bar */}
                <div className="mb-2">
                  <div className="flex justify-between text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                    <span>Tiến độ</span>
                    <span>0%</span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-page)" }}>
                    <div className="h-full w-0 rounded-full bg-primary-600" />
                  </div>
                </div>
                <div className="flex gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
                  <span className="flex items-center gap-1">
                    <span className="font-bold" style={{ color: "var(--text-primary)" }}>{lectures.length}</span>
                    &nbsp;Video
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="font-bold text-emerald-600">0</span>
                    &nbsp;Hoàn thành
                  </span>
                </div>
              </div>
            )}

            {/* Lecture list */}
            <div className="flex-1 overflow-y-auto py-2">
              {lectures.length === 0 ? (
                <p className="text-center text-sm py-8" style={{ color: "var(--text-muted)" }}>
                  Chưa có bài giảng
                </p>
              ) : (
                <div className="px-2 space-y-0.5">
                  {lectures.map((l, idx) => {
                    const isActive = l.id === selectedLecture;
                    return (
                      <button
                        key={l.id}
                        onClick={() => setSelectedLecture(l.id)}
                        className="w-full text-left rounded-lg px-3 py-2.5 transition-colors group"
                        style={{
                          backgroundColor: isActive ? "rgba(37,99,235,0.08)" : "transparent",
                        }}
                      >
                        <div className="flex items-start gap-2">
                          <PlayCircle
                            className="h-4 w-4 shrink-0 mt-0.5 transition-colors"
                            style={{ color: isActive ? "#2563eb" : "var(--text-muted)" }}
                          />
                          <div className="flex-1 min-w-0">
                            <p
                              className="text-xs font-medium leading-snug line-clamp-2"
                              style={{ color: isActive ? "#2563eb" : "var(--text-secondary)" }}
                            >
                              {idx + 1}. {l.title}
                            </p>
                            {l.duration != null && (
                              <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
                                <Clock className="h-3 w-3" />
                                {formatTime(l.duration)}
                              </p>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Chapter list (when a lecture is selected) — collapsible */}
            {chapters.length > 0 && (
              <div className="border-t shrink-0" style={{ borderColor: "var(--border)" }}>
                {/* Dropdown toggle */}
                <button
                  onClick={() => setChaptersOpen((o) => !o)}
                  className="w-full flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                    Video bài giảng
                  </span>
                  <ChevronDown
                    className="h-3.5 w-3.5 transition-transform duration-200"
                    style={{
                      color: "var(--text-muted)",
                      transform: chaptersOpen ? "rotate(180deg)" : "rotate(0deg)",
                    }}
                  />
                </button>

                {chaptersOpen && (
                  <div className="px-2 pb-2 space-y-0.5">
                    {chapters.map((ch, i) => {
                      const active = currentTime >= ch.start_time && currentTime < ch.end_time;
                      return (
                        <button
                          key={ch.id}
                          onClick={() => {
                            if (videoRef.current) videoRef.current.currentTime = ch.start_time;
                          }}
                          className="w-full text-left rounded-lg px-3 py-2 transition-colors"
                          style={{
                            borderLeft: active ? "3px solid #2563eb" : "3px solid transparent",
                            backgroundColor: active ? "rgba(37,99,235,0.07)" : "transparent",
                          }}
                        >
                          <p
                            className="text-xs font-medium truncate"
                            style={{ color: active ? "#2563eb" : "var(--text-secondary)" }}
                          >
                            {i + 1}. {ch.title}
                          </p>
                          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                            {formatTime(ch.start_time)}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </aside>

      {/* ═══════════════════════════════════════════════════════════════════
          CENTER — Video player
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Quiz toggle bar */}
        <div
          className="flex h-12 items-center justify-center border-b shrink-0 gap-3"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
        >
          <button
            onClick={() => setQuizEnabled((q) => !q)}
            className="flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition-colors hover:opacity-80"
            style={{
              borderColor: "var(--border)",
              color: quizEnabled ? "#2563eb" : "var(--text-secondary)",
              backgroundColor: quizEnabled ? "rgba(37,99,235,0.07)" : "var(--bg-page)",
            }}
          >
            {quizEnabled ? (
              <ToggleRight className="h-4 w-4 text-primary-600" />
            ) : (
              <ToggleLeft className="h-4 w-4" />
            )}
            Quiz giữa bài: {quizEnabled ? "Bật" : "Tắt"}
          </button>
        </div>

        {/* Video */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          <div className="w-full aspect-video bg-black shrink-0">
            <video
              ref={videoRef}
              className="w-full h-full object-contain cursor-pointer"
              onTimeUpdate={handleTimeUpdate}
              onDurationChange={() => {
                if (videoRef.current) setDuration(videoRef.current.duration || 0);
              }}
              onClick={() => {
                const v = videoRef.current;
                if (v) v.paused ? v.play() : v.pause();
              }}
              src={lecture?.video_url ? `/${lecture.video_url}` : undefined}
            />
          </div>

          {/* YouTube-style custom video controls */}
          <VideoControls
            videoRef={videoRef}
            currentTime={currentTime}
            duration={duration || lecture?.duration || 0}
            chapters={chapters}
            onSeek={(t) => {
              if (videoRef.current) videoRef.current.currentTime = t;
            }}
          />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          RIGHT PANEL — Lesson content + Transcript + AI Copilot
      ═══════════════════════════════════════════════════════════════════ */}
      <aside
        className="flex flex-col border-l shrink-0 transition-all duration-300 overflow-hidden"
        style={{
          width: rightCollapsed ? "3rem" : "22rem",
          borderColor: "var(--border)",
          backgroundColor: "var(--bg-card)",
        }}
      >
        {/* Panel header */}
        <div
          className="flex h-12 items-center border-b px-3 shrink-0 gap-2"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            onClick={() => setRightCollapsed((c) => !c)}
            className="rounded-lg p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0"
            style={{ color: "var(--text-muted)" }}
          >
            {rightCollapsed ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          {!rightCollapsed && (
            <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              Nội dung bài học
            </span>
          )}
        </div>

        {!rightCollapsed && (
          <>
            {/* Tabs */}
            <div className="flex border-b shrink-0" style={{ borderColor: "var(--border)" }}>
              {(["lesson", "transcript", "copilot"] as RightTab[]).map((tab) => {
                const labels: Record<RightTab, { label: string; icon: React.ReactNode }> = {
                  lesson:     { label: "Bài giảng",  icon: <FileText className="h-3.5 w-3.5" /> },
                  transcript: { label: "Transcript", icon: <AlignLeft className="h-3.5 w-3.5" /> },
                  copilot:    { label: "AI",          icon: <Bot className="h-3.5 w-3.5" /> },
                };
                const { label, icon } = labels[tab];
                const isActive = rightTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setRightTab(tab)}
                    className="flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors relative"
                    style={{
                      color: isActive ? "#2563eb" : "var(--text-muted)",
                    }}
                  >
                    {icon}
                    {label}
                    {isActive && (
                      <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 rounded-t" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Tab content */}
            {rightTab === "lesson" && (
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {lecture ? (
                  <>
                    <div
                      className="flex items-center gap-2 rounded-lg border p-3 cursor-pointer hover:opacity-80 transition-opacity"
                      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}
                    >
                      <FileText className="h-5 w-5 text-primary-600 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                          Slide bài giảng
                        </p>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                          {chapters.length} slides
                        </p>
                      </div>
                    </div>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                      {lecture.description ?? "Không có mô tả cho bài giảng này."}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-center py-8" style={{ color: "var(--text-muted)" }}>
                    Chọn bài giảng để xem nội dung.
                  </p>
                )}
              </div>
            )}

            {rightTab === "transcript" && (
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {chapters.length === 0 ? (
                  <p className="text-sm text-center py-8" style={{ color: "var(--text-muted)" }}>
                    Chưa có transcript.
                  </p>
                ) : (
                  chapters.map((ch) => {
                    const active = currentTime >= ch.start_time && currentTime < ch.end_time;
                    return (
                      <button
                        key={ch.id}
                        onClick={() => {
                          if (videoRef.current) videoRef.current.currentTime = ch.start_time;
                        }}
                        className="w-full text-left rounded-lg p-3 transition-colors"
                        style={{
                          backgroundColor: active ? "rgba(37,99,235,0.08)" : "transparent",
                        }}
                      >
                        <p
                          className="text-xs font-semibold mb-1"
                          style={{ color: active ? "#2563eb" : "var(--text-muted)" }}
                        >
                          {formatTime(ch.start_time)}
                        </p>
                        <p
                          className="text-sm leading-relaxed"
                          style={{ color: active ? "var(--text-primary)" : "var(--text-secondary)" }}
                        >
                          {ch.summary || ch.title}
                        </p>
                      </button>
                    );
                  })
                )}
              </div>
            )}

            {/* ── AI Copilot tab ── */}
            {rightTab === "copilot" && (
              <div className="flex flex-1 flex-col overflow-hidden">
                {/* Messages area */}
                <div className="flex-1 overflow-y-auto">
                  {!hasMessages ? (
                    /* Welcome state */
                    <div className="flex flex-col items-center justify-center h-full px-5 py-8 gap-5 text-center">
                      {/* Sparkle icon */}
                      <div
                        className="flex h-16 w-16 items-center justify-center rounded-full"
                        style={{ backgroundColor: "rgba(37,99,235,0.08)" }}
                      >
                        <Sparkles className="h-8 w-8 text-primary-600" />
                      </div>

                      <div className="space-y-1.5">
                        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                          Xin chào! Tôi là AI Copilot
                        </h3>
                        <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                          Tôi có thể giúp bạn tóm tắt bài học, giải thích khái niệm khó hoặc phân tích dữ liệu admin.
                        </p>
                      </div>

                      {/* Quick actions */}
                      <div className="w-full space-y-2">
                        <button
                          onClick={() => handleSend("Tóm tắt nội dung bài học này cho tôi")}
                          className="flex w-full items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm transition-colors hover:opacity-80 text-left"
                          style={{
                            borderColor: "var(--border)",
                            backgroundColor: "var(--bg-page)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          <Zap className="h-4 w-4 text-amber-500 shrink-0" />
                          Tóm tắt trang này
                        </button>
                        <button
                          onClick={() => handleSend("Lộ trình học tiếp theo của tôi là gì?")}
                          className="flex w-full items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm transition-colors hover:opacity-80 text-left"
                          style={{
                            borderColor: "var(--border)",
                            backgroundColor: "var(--bg-page)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          <BookOpen className="h-4 w-4 text-emerald-500 shrink-0" />
                          Lộ trình tiếp theo
                        </button>
                        <button
                          onClick={() => handleSend("Giải thích các thuật ngữ quan trọng trong bài này")}
                          className="flex w-full items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm transition-colors hover:opacity-80 text-left"
                          style={{
                            borderColor: "var(--border)",
                            backgroundColor: "var(--bg-page)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          <MessageSquare className="h-4 w-4 text-violet-500 shrink-0" />
                          Giải thích thuật ngữ
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Conversation */
                    <div className="flex flex-col gap-3 p-3">
                      {messages.map((msg, idx) => (
                        <div key={idx} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                          {msg.role !== "user" && (
                            <div
                              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full mt-0.5 mr-2"
                              style={{ backgroundColor: "rgba(37,99,235,0.1)" }}
                            >
                              <Bot className="h-3.5 w-3.5 text-primary-600" />
                            </div>
                          )}
                          <div className="max-w-[85%]">
                            <div
                              className="rounded-2xl px-3 py-2 text-sm leading-relaxed"
                              style={
                                msg.role === "user"
                                  ? { backgroundColor: "#2563eb", color: "white", borderBottomRightRadius: "0.25rem" }
                                  : msg.role === "error"
                                  ? { backgroundColor: "rgba(239,68,68,0.1)", color: "#ef4444", borderBottomLeftRadius: "0.25rem" }
                                  : { backgroundColor: "var(--bg-page)", color: "var(--text-primary)", borderBottomLeftRadius: "0.25rem" }
                              }
                            >
                              {msg.content || (
                                <span className="flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
                                  <Loader2 className="h-3 w-3 animate-spin" />
                                  Đang trả lời...
                                </span>
                              )}
                            </div>
                            {msg.role === "ai" && msg.id && msg.content && (
                              <div className="flex gap-2 mt-1 ml-1">
                                <button
                                  onClick={() => rateAnswer(idx, msg.id!, 1)}
                                  disabled={msg.rating !== undefined && msg.rating !== null}
                                  className="transition-colors"
                                  style={{ color: msg.rating === 1 ? "#4ade80" : "var(--text-muted)" }}
                                >
                                  <ThumbsUp className="h-3 w-3" />
                                </button>
                                <button
                                  onClick={() => rateAnswer(idx, msg.id!, -1)}
                                  disabled={msg.rating !== undefined && msg.rating !== null}
                                  className="transition-colors"
                                  style={{ color: msg.rating === -1 ? "#f87171" : "var(--text-muted)" }}
                                >
                                  <ThumbsDown className="h-3 w-3" />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      <div ref={chatEndRef} />
                    </div>
                  )}
                </div>

                {/* Chat input */}
                <div
                  className="border-t p-3 shrink-0"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div
                    className="flex items-end gap-2 rounded-xl border px-3 py-2 transition-colors focus-within:border-primary-500"
                    style={{
                      borderColor: "var(--border)",
                      backgroundColor: "var(--bg-page)",
                    }}
                  >
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      placeholder="Gửi tin nhắn cho AI..."
                      rows={1}
                      className="flex-1 resize-none bg-transparent outline-none text-sm"
                      style={{ color: "var(--text-primary)", maxHeight: "6rem" }}
                    />
                    <button
                      onClick={() => handleSend()}
                      disabled={streaming || !input.trim()}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-all disabled:opacity-40"
                      style={{ backgroundColor: "#2563eb", color: "white" }}
                    >
                      {streaming ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
