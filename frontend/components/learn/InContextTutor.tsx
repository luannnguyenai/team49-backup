"use client";

// components/learn/InContextTutor.tsx
// In-context AI Tutor panel embedded within the learning unit shell.
// Reuses the existing /api/lectures/ask endpoint for Q&A streaming.

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Send, X, ThumbsUp, ThumbsDown, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

interface ChatMessage {
  id?: number;
  role: "user" | "ai" | "error";
  content: string;
  rating?: number | null;
}

interface InContextTutorProps {
  lectureId: string;
  currentTime: number;
  captureFrame: () => string | null;
  contextBindingId?: string;
  unitTitle: string;
  onClose: () => void;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function InContextTutor({
  lectureId,
  currentTime,
  captureFrame,
  unitTitle,
  onClose,
}: InContextTutorProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Rate answer
  const rateAnswer = async (msgIdx: number, qaId: number, rating: number) => {
    try {
      await api.post(`/api/history/${qaId}/rate`, { rating });
      setMessages((prev) =>
        prev.map((m, i) => (i === msgIdx ? { ...m, rating } : m)),
      );
    } catch {}
  };

  // Send message
  const handleSend = useCallback(async () => {
    const q = input.trim();
    if (!q || streaming || !lectureId) return;

    setInput("");
    setStreaming(true);
    const img = captureFrame();

    const userMsg: ChatMessage = { role: "user", content: q };
    const aiPlaceholder: ChatMessage = { role: "ai", content: "" };

    setMessages((prev) => [...prev, userMsg, aiPlaceholder]);
    const aiIdx = messages.length + 1;

    try {
      const resp = await fetch("/api/lectures/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lecture_id: lectureId,
          current_timestamp: currentTime,
          question: q,
          image_base64: img,
        }),
      });

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
                prev.map((m, i) =>
                  i === aiIdx ? { ...m, role: "error", content: data.e } : m,
                ),
              );
              hasError = true;
              break;
            }
            if (data.status) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? { ...m, content: fullText || data.status }
                    : m,
                ),
              );
            }
            if (data.a) {
              fullText += data.a;
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx ? { ...m, content: fullText } : m,
                ),
              );
            }
            if (data.qa_id) qaId = data.qa_id;
          } catch {}
        }
      }

      if (qaId) {
        setMessages((prev) =>
          prev.map((m, i) => (i === aiIdx ? { ...m, id: qaId } : m)),
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection error";
      setMessages((prev) =>
        prev.map((m, i) =>
          i === aiIdx ? { ...m, role: "error", content: msg } : m,
        ),
      );
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }, [input, streaming, lectureId, currentTime, messages.length, captureFrame]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex h-12 items-center justify-between border-b px-4 shrink-0"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            AI Tutor
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
          style={{ color: "var(--text-muted)" }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!hasMessages && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg">
              <svg
                className="h-7 w-7 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                />
              </svg>
            </div>
            <p
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-primary)" }}
            >
              Ask anything about this lecture
            </p>
            <p
              className="text-xs max-w-52"
              style={{ color: "var(--text-muted)" }}
            >
              Your questions are linked to{" "}
              <span className="font-medium">{unitTitle}</span> at the current
              video timestamp.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-md"
                  : msg.role === "error"
                    ? "bg-red-50 text-red-700 border border-red-200 rounded-bl-md"
                    : "rounded-bl-md"
              }`}
              style={
                msg.role === "ai"
                  ? {
                      backgroundColor: "var(--bg-page)",
                      color: "var(--text-primary)",
                    }
                  : undefined
              }
            >
              {msg.role === "ai" ? (
                <div className="prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>{msg.content || "..."}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}

              {/* Rating buttons for AI messages */}
              {msg.role === "ai" && msg.id && msg.content && (
                <div className="mt-2 flex items-center gap-2 border-t pt-2 border-slate-200/50">
                  <button
                    onClick={() => rateAnswer(idx, msg.id!, 1)}
                    className={`p-1 rounded transition-colors ${
                      msg.rating === 1
                        ? "text-emerald-500"
                        : "text-slate-400 hover:text-emerald-500"
                    }`}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => rateAnswer(idx, msg.id!, -1)}
                    className={`p-1 rounded transition-colors ${
                      msg.rating === -1
                        ? "text-red-400"
                        : "text-slate-400 hover:text-red-400"
                    }`}
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
      <div
        className="border-t p-3 shrink-0"
        style={{ borderColor: "var(--border)" }}
      >
        <div
          className="flex items-end gap-2 rounded-xl border p-2"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-page)",
          }}
        >
          <textarea
            ref={inputRef}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm outline-none"
            style={{ color: "var(--text-primary)" }}
            placeholder="Ask about this lecture..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={streaming}
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className="shrink-0 rounded-lg p-2 transition-colors disabled:opacity-30"
            style={{ color: "#2563eb" }}
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
  );
}
