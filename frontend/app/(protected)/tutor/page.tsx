"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Send,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  ChevronLeft,
  ChevronRight,
  FileText,
  AlignLeft,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";

// ---- Types ----
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

// ---- Helpers ----
function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

export default function TutorPage() {
  // ---- State ----
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [selectedLecture, setSelectedLecture] = useState<string>("");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "ai", content: "Chào bạn! Hãy chọn bài giảng và đặt câu hỏi bất cứ lúc nào trong khi xem video." },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [quizEnabled, setQuizEnabled] = useState(false);
  const [rightTab, setRightTab] = useState<"lesson" | "transcript">("transcript");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ---- Progress tracking ----
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

  // Save progress every 10s while playing
  useEffect(() => {
    const interval = setInterval(() => {
      if (videoRef.current && !videoRef.current.paused) saveProgress();
    }, 10_000);
    return () => clearInterval(interval);
  }, [saveProgress]);

  // ---- Load lectures on mount ----
  useEffect(() => {
    api.get<Lecture[]>("/api/lectures").then((r) => {
      setLectures(r.data);
      if (r.data.length > 0) setSelectedLecture(r.data[0].id);
    }).catch(() => {});
  }, []);

  // ---- Load chapters + restore progress when lecture changes ----
  useEffect(() => {
    if (!selectedLecture) return;
    api.get<Chapter[]>(`/api/lectures/${selectedLecture}/toc`).then((r) => {
      setChapters(r.data);
    }).catch(() => setChapters([]));

    api.get<Record<string, number>>(`/api/progress/${sessionId.current}`).then((r) => {
      const ts = r.data[selectedLecture];
      if (ts && ts > 1 && videoRef.current) {
        videoRef.current.currentTime = ts;
      }
    }).catch(() => {});
  }, [selectedLecture]);

  // ---- Auto-scroll chat ----
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---- Video time update ----
  const handleTimeUpdate = () => {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  };

  // ---- Capture frame ----
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

  // ---- Rate answer ----
  const rateAnswer = async (msgIdx: number, qaId: number, rating: number) => {
    try {
      await api.post(`/api/history/${qaId}/rate`, { rating });
      setMessages((prev) =>
        prev.map((m, i) => (i === msgIdx ? { ...m, rating } : m))
      );
    } catch {}
  };

  // ---- Send question ----
  const handleSend = async () => {
    const q = input.trim();
    if (!q || streaming || !selectedLecture) return;

    setInput("");
    setStreaming(true);
    const img = captureFrame();

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    const aiIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: "ai", content: "" }]);

    try {
      const resp = await fetch(
        `${typeof window !== "undefined" ? "" : "http://localhost:8000"}/api/lectures/ask`,
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        for (const line of text.split("\n")) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line.trim());
            if (data.e) {
              setMessages((prev) =>
                prev.map((m, i) => i === aiIdx ? { ...m, role: "error", content: data.e } : m)
              );
              break;
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
  };

  const lecture = lectures.find((l) => l.id === selectedLecture);
  const activeChapter = chapters.find(
    (ch) => currentTime >= ch.start_time && currentTime < ch.end_time
  );

  return (
    <div
      className="flex h-[calc(100vh-4.5rem)] overflow-hidden -mx-4 -mt-4 md:-mx-6 md:-mt-6"
      style={{ backgroundColor: "var(--bg-page)" }}
    >
      {/* ── LEFT PANEL: Course content ── */}
      <aside
        className="flex flex-col border-r shrink-0 transition-all duration-300 overflow-hidden"
        style={{
          width: leftCollapsed ? "3rem" : "18rem",
          borderColor: "var(--border)",
          backgroundColor: "var(--bg-card)",
        }}
      >
        {/* Panel header */}
        <div
          className="flex h-12 items-center justify-between border-b px-3 shrink-0"
          style={{ borderColor: "var(--border)" }}
        >
          {!leftCollapsed && (
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Nội dung khóa học
            </span>
          )}
          <button
            onClick={() => setLeftCollapsed((c) => !c)}
            className="ml-auto rounded-lg p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            style={{ color: "var(--text-muted)" }}
          >
            {leftCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {!leftCollapsed && (
          <div className="flex flex-col flex-1 overflow-y-auto p-3 gap-4">
            {/* Lecture selector */}
            <select
              value={selectedLecture}
              onChange={(e) => setSelectedLecture(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm"
              style={{
                backgroundColor: "var(--bg-page)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
            >
              {lectures.map((l) => (
                <option key={l.id} value={l.id}>{l.title}</option>
              ))}
              {lectures.length === 0 && <option>Chưa có bài giảng</option>}
            </select>

            {/* Lecture info */}
            {lecture && (
              <div className="space-y-2">
                <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {lecture.title}
                </p>
                {lecture.description && (
                  <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                    {lecture.description}
                  </p>
                )}
                {/* Progress */}
                <div>
                  <div className="flex justify-between text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                    <span>Tiến độ học tập</span>
                    <span>0%</span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--bg-page)" }}>
                    <div className="h-full w-0 rounded-full bg-primary-600" />
                  </div>
                </div>
                {/* Stats */}
                <div className="flex gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
                  <span className="flex items-center gap-1">
                    <span className="font-semibold text-primary-600">{chapters.length || 1}</span> Video
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="font-semibold text-emerald-600">0</span> Hoàn thành
                  </span>
                </div>
              </div>
            )}

            {/* Video list */}
            {chapters.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Video bài giảng
                </p>
                {chapters.map((ch, i) => {
                  const active = currentTime >= ch.start_time && currentTime < ch.end_time;
                  return (
                    <button
                      key={ch.id}
                      onClick={() => {
                        if (videoRef.current) videoRef.current.currentTime = ch.start_time;
                      }}
                      className="w-full text-left rounded-lg px-3 py-2 text-sm transition-colors"
                      style={{
                        borderLeft: active ? "3px solid #2563eb" : "3px solid transparent",
                        backgroundColor: active ? "rgba(37,99,235,0.07)" : "transparent",
                        color: active ? "#2563eb" : "var(--text-secondary)",
                      }}
                    >
                      <p className="font-medium truncate">
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
      </aside>

      {/* ── CENTER: Video player ── */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Quiz toggle bar */}
        <div
          className="flex h-12 items-center justify-center border-b shrink-0"
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
              controls
              className="w-full h-full object-contain"
              onTimeUpdate={handleTimeUpdate}
              src={lecture?.video_url ? `/${lecture.video_url}` : undefined}
            />
          </div>

          {/* Video title + timestamp */}
          <div className="px-6 py-4" style={{ backgroundColor: "var(--bg-card)" }}>
            <h2 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
              {activeChapter?.title ?? lecture?.title ?? "Chọn bài giảng"}
            </h2>
            <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
              {formatTime(currentTime)} / {formatTime(lecture?.duration ?? 0)}
            </p>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL: Lesson content + Transcript ── */}
      <aside
        className="flex flex-col border-l shrink-0 transition-all duration-300 overflow-hidden"
        style={{
          width: rightCollapsed ? "3rem" : "20rem",
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
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Nội dung bài học
            </span>
          )}
        </div>

        {!rightCollapsed && (
          <>
            {/* Tabs */}
            <div
              className="flex border-b shrink-0"
              style={{ borderColor: "var(--border)" }}
            >
              <button
                onClick={() => setRightTab("lesson")}
                className="flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors"
                style={{
                  borderBottom: rightTab === "lesson" ? "2px solid #2563eb" : "2px solid transparent",
                  color: rightTab === "lesson" ? "#2563eb" : "var(--text-muted)",
                }}
              >
                <FileText className="h-3.5 w-3.5" />
                Bài giảng
              </button>
              <button
                onClick={() => setRightTab("transcript")}
                className="flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors"
                style={{
                  borderBottom: rightTab === "transcript" ? "2px solid #2563eb" : "2px solid transparent",
                  color: rightTab === "transcript" ? "#2563eb" : "var(--text-muted)",
                }}
              >
                <AlignLeft className="h-3.5 w-3.5" />
                Transcript
              </button>
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto">
              {rightTab === "lesson" ? (
                <div className="p-4 space-y-3">
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
              ) : (
                /* Transcript = chapters */
                <div className="p-3 space-y-3">
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
            </div>

            {/* Chat input — always visible at bottom */}
            <div className="border-t p-3 shrink-0" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs font-semibold mb-2" style={{ color: "var(--text-muted)" }}>
                Hỏi AI Tutor
              </p>
              <div className="flex gap-2">
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
                  placeholder="Đặt câu hỏi về bài giảng..."
                  rows={2}
                  className="flex-1 rounded-lg border px-3 py-2 text-sm resize-none outline-none focus:ring-1 focus:ring-primary-500"
                  style={{
                    backgroundColor: "var(--bg-page)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={streaming || !input.trim()}
                  className="self-end rounded-lg px-3 py-2 transition-opacity disabled:opacity-40"
                  style={{ backgroundColor: "var(--primary-600, #2563eb)", color: "white" }}
                >
                  {streaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>

              {/* Recent AI messages */}
              {messages.filter((m) => m.role !== "user").length > 1 && (
                <div className="mt-3 space-y-2 max-h-36 overflow-y-auto">
                  {messages
                    .filter((m) => m.content)
                    .slice(-4)
                    .map((msg, idx) => (
                      <div key={idx}>
                        <div
                          className="rounded-lg px-3 py-2 text-xs leading-relaxed"
                          style={
                            msg.role === "user"
                              ? { backgroundColor: "rgba(37,99,235,0.1)", color: "#2563eb" }
                              : msg.role === "error"
                              ? { backgroundColor: "rgba(239,68,68,0.1)", color: "#f87171" }
                              : { backgroundColor: "var(--bg-page)", color: "var(--text-secondary)" }
                          }
                        >
                          {msg.content}
                        </div>
                        {msg.role === "ai" && msg.id && msg.content && (
                          <div className="flex gap-1 mt-1">
                            <button
                              onClick={() => rateAnswer(messages.indexOf(msg), msg.id!, 1)}
                              disabled={msg.rating !== undefined && msg.rating !== null}
                              style={{ color: msg.rating === 1 ? "#4ade80" : "var(--text-muted)" }}
                            >
                              <ThumbsUp className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => rateAnswer(messages.indexOf(msg), msg.id!, -1)}
                              disabled={msg.rating !== undefined && msg.rating !== null}
                              style={{ color: msg.rating === -1 ? "#f87171" : "var(--text-muted)" }}
                            >
                              <ThumbsDown className="h-3 w-3" />
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
