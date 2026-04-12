"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { Send, ThumbsUp, ThumbsDown, Loader2, Video } from "lucide-react";

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

    // Restore progress
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

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: q }]);

    // Add placeholder AI message
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
                prev.map((m, i) =>
                  i === aiIdx ? { ...m, role: "error", content: data.e } : m
                )
              );
              break;
            }
            if (data.a) {
              fullText += data.a;
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx ? { ...m, content: fullText } : m
                )
              );
            }
            if (data.qa_id) qaId = data.qa_id;
          } catch {}
        }
      }

      // Attach qa_id for rating
      if (qaId) {
        setMessages((prev) =>
          prev.map((m, i) => (i === aiIdx ? { ...m, id: qaId } : m))
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection error";
      setMessages((prev) =>
        prev.map((m, i) =>
          i === aiIdx ? { ...m, role: "error", content: msg } : m
        )
      );
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  };

  const lecture = lectures.find((l) => l.id === selectedLecture);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* ---- Left: Video + ToC ---- */}
      <div className="flex flex-1 flex-col gap-3 min-w-0">
        {/* Lecture selector */}
        <div className="flex items-center gap-3">
          <Video className="h-5 w-5 shrink-0" style={{ color: "var(--text-muted)" }} />
          <select
            value={selectedLecture}
            onChange={(e) => setSelectedLecture(e.target.value)}
            className="flex-1 rounded-lg border px-3 py-2 text-sm"
            style={{
              backgroundColor: "var(--bg-card)",
              borderColor: "var(--border)",
              color: "var(--text-primary)",
            }}
          >
            {lectures.map((l) => (
              <option key={l.id} value={l.id}>
                {l.title}
              </option>
            ))}
            {lectures.length === 0 && <option>No lectures found</option>}
          </select>
          <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
            {formatTime(currentTime)}
          </span>
        </div>

        {/* Video player */}
        <div className="relative rounded-xl overflow-hidden border" style={{ borderColor: "var(--border)" }}>
          <video
            ref={videoRef}
            controls
            className="w-full aspect-video bg-black"
            onTimeUpdate={handleTimeUpdate}
            src={lecture?.video_url ? `/${lecture.video_url}` : undefined}
          />
        </div>

        {/* Chapters / ToC */}
        {chapters.length > 0 && (
          <div
            className="flex-1 overflow-y-auto rounded-xl border p-3 space-y-1"
            style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
          >
            <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
              Mục lục
            </h3>
            {chapters.map((ch) => {
              const active = currentTime >= ch.start_time && currentTime < ch.end_time;
              return (
                <button
                  key={ch.id}
                  onClick={() => {
                    if (videoRef.current) videoRef.current.currentTime = ch.start_time;
                  }}
                  className="w-full text-left rounded-lg px-3 py-2 text-sm transition-colors hover:opacity-80"
                  style={{
                    backgroundColor: active ? "var(--primary-50, rgba(59,130,246,0.1))" : "transparent",
                    color: active ? "var(--primary-600, #2563eb)" : "var(--text-secondary)",
                  }}
                >
                  <span className="font-mono text-xs mr-2" style={{ color: "var(--text-muted)" }}>
                    {formatTime(ch.start_time)}
                  </span>
                  {ch.title}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ---- Right: Chat ---- */}
      <div
        className="flex w-96 shrink-0 flex-col rounded-xl border overflow-hidden"
        style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        {/* Chat header */}
        <div className="border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            AI Tutor Chat
          </h3>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Hỏi bất cứ điều gì về bài giảng
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className="max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed"
                style={
                  msg.role === "user"
                    ? { backgroundColor: "var(--primary-600, #2563eb)", color: "white" }
                    : msg.role === "error"
                    ? { backgroundColor: "rgba(239,68,68,0.1)", color: "#f87171" }
                    : { backgroundColor: "var(--bg-page)", color: "var(--text-primary)" }
                }
              >
                {msg.content || (
                  <span className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                    <Loader2 className="h-3 w-3 animate-spin" /> Thinking...
                  </span>
                )}

                {/* Rating buttons for AI messages with qa_id */}
                {msg.role === "ai" && msg.id && msg.content && (
                  <div className="flex gap-1 mt-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                    <button
                      onClick={() => rateAnswer(idx, msg.id!, 1)}
                      className="rounded p-1 transition-colors hover:opacity-80"
                      style={{
                        color: msg.rating === 1 ? "#4ade80" : "var(--text-muted)",
                        backgroundColor: msg.rating === 1 ? "rgba(74,222,128,0.15)" : "transparent",
                      }}
                      disabled={msg.rating !== undefined && msg.rating !== null}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => rateAnswer(idx, msg.id!, -1)}
                      className="rounded p-1 transition-colors hover:opacity-80"
                      style={{
                        color: msg.rating === -1 ? "#f87171" : "var(--text-muted)",
                        backgroundColor: msg.rating === -1 ? "rgba(248,113,113,0.15)" : "transparent",
                      }}
                      disabled={msg.rating !== undefined && msg.rating !== null}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="border-t p-3" style={{ borderColor: "var(--border)" }}>
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
              placeholder="Hỏi Gia sư..."
              rows={2}
              className="flex-1 rounded-lg border px-3 py-2 text-sm resize-none outline-none focus:ring-1"
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
        </div>
      </div>
    </div>
  );
}
