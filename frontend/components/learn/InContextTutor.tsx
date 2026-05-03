"use client";

// components/learn/InContextTutor.tsx
// In-context AI Tutor panel embedded within the learning unit shell.
// Reuses the existing /api/lectures/ask endpoint for Q&A streaming.

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Send, X, ThumbsUp, ThumbsDown, Loader2, Check } from "lucide-react";
import { api } from "@/lib/api";
import {
  buildTutorConversationKey,
  loadTutorConversation,
  saveTutorConversation,
  type StoredTutorMessage,
} from "@/lib/tutorSessionHistory";
import { useAuthStore } from "@/stores/authStore";

// ── Types ──────────────────────────────────────────────────────────────────

interface ChatMessage {
  localId: string;
  id?: number;
  role: "user" | "ai" | "error";
  content: string;
  senderName: string;
  sentAt: string;
  rating?: number | null;
  isPending?: boolean;
  statusText?: string | null;
  statusSteps?: string[];
}

function formatMessageTime(date: Date): string {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function waitForNextPaint(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, 0);
  });
}

const MIN_STATUS_VISIBLE_MS = 450;

function appendStatusStep(steps: string[] | undefined, nextStatus: string): string[] {
  const normalizedStatus = nextStatus.trim();
  if (!normalizedStatus) {
    return steps ?? [];
  }

  const previousSteps = steps ?? [];
  if (previousSteps[previousSteps.length - 1] === normalizedStatus) {
    return previousSteps;
  }

  if (previousSteps.includes(normalizedStatus)) {
    return previousSteps;
  }

  return [...previousSteps, normalizedStatus];
}

interface InContextTutorProps {
  lessonKey?: string;
  lectureId: string;
  currentTime: number;
  captureFrame: () => string | null;
  contextBindingId?: string;
  unitTitle: string;
  onClose?: () => void;
  suggestions?: string[];
}

// ── Component ───────────────────────────────────────────────────────────────

export default function InContextTutor({
  lessonKey,
  lectureId,
  currentTime,
  captureFrame,
  contextBindingId,
  unitTitle,
  onClose,
  suggestions = [],
}: InContextTutorProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const userFullName = useAuthStore((state) => state.user?.full_name?.trim() || "You");
  const resolvedLessonKey = lessonKey?.trim() || lectureId.trim();
  const conversationKey = resolvedLessonKey
    ? buildTutorConversationKey(resolvedLessonKey, contextBindingId)
    : null;

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messageIdRef = useRef(0);
  const loadedConversationKeyRef = useRef<string | null>(null);

  const nextMessageId = useCallback(() => {
    messageIdRef.current += 1;
    return `chat-msg-${messageIdRef.current}`;
  }, []);

  useEffect(() => {
    if (!conversationKey || loadedConversationKeyRef.current !== conversationKey) {
      return;
    }

    const persistedMessages: StoredTutorMessage[] = messages
      .filter((message) => !message.isPending)
      .map(({ id, role, content, senderName, sentAt, rating }) => ({
        id,
        role,
        content,
        senderName,
        sentAt,
        rating,
      }));

    saveTutorConversation(conversationKey, persistedMessages);
  }, [conversationKey, messages]);

  useEffect(() => {
    if (!conversationKey) {
      loadedConversationKeyRef.current = null;
      setMessages([]);
      return;
    }

    const storedMessages = loadTutorConversation(conversationKey);
    const hydratedMessages = storedMessages.map((message) => ({
      ...message,
      localId: nextMessageId(),
      isPending: false,
      statusText: null,
      statusSteps: [],
    }));

    loadedConversationKeyRef.current = conversationKey;
    setMessages(hydratedMessages);
  }, [conversationKey, nextMessageId]);

  // Auto-scroll
  useEffect(() => {
    if (typeof chatEndRef.current?.scrollIntoView === "function") {
      chatEndRef.current.scrollIntoView({
        behavior: streaming ? "auto" : "smooth",
      });
    }
  }, [messages, streaming]);

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
  const handleSend = useCallback(async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || streaming || !lectureId) return;

    setInput("");
    setStreaming(true);
    const img = captureFrame();
    const sentAt = formatMessageTime(new Date());

    const userMsg: ChatMessage = {
      localId: nextMessageId(),
      role: "user",
      content: q,
      senderName: userFullName,
      sentAt,
    };
    const aiPlaceholder: ChatMessage = {
      localId: nextMessageId(),
      role: "ai",
      content: "",
      senderName: "AI Tutor",
      sentAt,
      isPending: true,
      statusText: null,
      statusSteps: [],
    };

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
          context_binding_id: contextBindingId,
          image_base64: img,
        }),
      });

      if (!resp.ok) {
        let detail = `Tutor request failed (${resp.status})`;
        try {
          const payload = await resp.json();
          if (typeof payload?.detail === "string" && payload.detail.trim()) {
            detail = payload.detail;
          }
        } catch {
          try {
            const text = await resp.text();
            if (text.trim()) detail = text.trim();
          } catch {}
        }
        throw new Error(detail);
      }

      if (!resp.body) {
        throw new Error("Tutor response stream was empty");
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      let qaId: number | undefined;
      let hasError = false;
      let buffer = "";
      let pendingStatusNeedsPaint = false;
      let lastPendingStatusAt = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (hasError) break;

        buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
        const lines = buffer.split("\n");
        buffer = done ? "" : lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line.trim());
            if (data.e) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx ? { ...m, role: "error", content: data.e, isPending: false } : m,
                ),
              );
              hasError = true;
              break;
            }
            if (data.blocked && data.message) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? { ...m, role: "error", content: data.message, isPending: false }
                    : m,
                ),
              );
              hasError = true;
              break;
            }
            if (data.detail) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? { ...m, role: "error", content: String(data.detail), isPending: false }
                    : m,
                ),
              );
              hasError = true;
              break;
            }
            if (data.status) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? {
                        ...m,
                        isPending: !fullText,
                        statusText: String(data.status),
                        statusSteps: appendStatusStep(m.statusSteps, String(data.status)),
                      }
                    : m,
                ),
              );
              if (!fullText) {
                pendingStatusNeedsPaint = true;
                lastPendingStatusAt = Date.now();
              }
            }
            if (data.a) {
              if (!fullText && pendingStatusNeedsPaint) {
                await waitForNextPaint();
                const remainingStatusTime = MIN_STATUS_VISIBLE_MS - (Date.now() - lastPendingStatusAt);
                if (remainingStatusTime > 0) {
                  await new Promise((resolve) => window.setTimeout(resolve, remainingStatusTime));
                }
                pendingStatusNeedsPaint = false;
              }
              fullText += data.a;
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? {
                        ...m,
                        content: fullText,
                        isPending: false,
                        statusText: null,
                        statusSteps: [],
                      }
                    : m,
                ),
              );
            }
            if (data.qa_id) qaId = data.qa_id;
          } catch {}
        }

        if (done) {
          const tail = buffer.trim();
          if (tail && !hasError) {
            try {
              const data = JSON.parse(tail);
              if (data.e) {
                setMessages((prev) =>
                  prev.map((m, i) =>
                    i === aiIdx ? { ...m, role: "error", content: data.e, isPending: false } : m,
                  ),
                );
              } else if (data.blocked && data.message) {
                setMessages((prev) =>
                  prev.map((m, i) =>
                    i === aiIdx
                      ? { ...m, role: "error", content: data.message, isPending: false }
                      : m,
                  ),
                );
              } else if (data.detail) {
                setMessages((prev) =>
                  prev.map((m, i) =>
                    i === aiIdx
                      ? { ...m, role: "error", content: String(data.detail), isPending: false }
                      : m,
                  ),
                );
              } else {
                if (data.status) {
                  setMessages((prev) =>
                    prev.map((m, i) =>
                      i === aiIdx
                        ? {
                            ...m,
                            isPending: !fullText,
                            statusText: String(data.status),
                            statusSteps: appendStatusStep(m.statusSteps, String(data.status)),
                          }
                        : m,
                    ),
                  );
                  if (!fullText) {
                    pendingStatusNeedsPaint = true;
                    lastPendingStatusAt = Date.now();
                  }
                }
                if (data.a) {
                  if (!fullText && pendingStatusNeedsPaint) {
                    await waitForNextPaint();
                    const remainingStatusTime = MIN_STATUS_VISIBLE_MS - (Date.now() - lastPendingStatusAt);
                    if (remainingStatusTime > 0) {
                      await new Promise((resolve) => window.setTimeout(resolve, remainingStatusTime));
                    }
                    pendingStatusNeedsPaint = false;
                  }
                  fullText += data.a;
                  setMessages((prev) =>
                    prev.map((m, i) =>
                      i === aiIdx
                        ? {
                            ...m,
                            content: fullText,
                            isPending: false,
                            statusText: null,
                            statusSteps: [],
                          }
                        : m,
                    ),
                  );
                }
                if (data.qa_id) qaId = data.qa_id;
              }
            } catch {}
          }
          break;
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
          i === aiIdx ? { ...m, role: "error", content: msg, senderName: "AI Tutor", isPending: false } : m,
        ),
      );
    } finally {
      setStreaming(false);
      window.setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  }, [input, streaming, lectureId, currentTime, contextBindingId, messages.length, captureFrame, nextMessageId]);

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
        {onClose ? (
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            style={{ color: "var(--text-muted)" }}
          >
            <span className="sr-only">Close tutor</span>
            <X className="h-4 w-4" />
          </button>
        ) : null}
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
            key={msg.localId}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`mb-1 flex items-center gap-2 px-1 text-[11px] font-medium ${
                msg.role === "user" ? "justify-end text-slate-400" : "justify-start text-slate-500"
              }`}
            >
              <span>{msg.senderName}</span>
              <span aria-hidden="true">•</span>
              <time dateTime={msg.sentAt}>{msg.sentAt}</time>
            </div>

            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-md"
                  : msg.role === "error"
                    ? "bg-red-50 text-red-700 border border-red-200 rounded-bl-md"
                    : "rounded-bl-md transition-all duration-200"
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
                msg.isPending ? (
                  <div
                    aria-live="polite"
                    className="space-y-2 italic"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {(msg.statusSteps?.length ? msg.statusSteps : msg.statusText ? [msg.statusText] : []).map(
                      (step, stepIdx, allSteps) => {
                        const isCurrentStep = stepIdx === allSteps.length - 1;

                        return (
                          <div
                            key={`${msg.localId}-status-${stepIdx}`}
                            className="flex items-start gap-2"
                            style={{
                              color: isCurrentStep ? "var(--text-secondary)" : "var(--text-muted)",
                            }}
                          >
                            {isCurrentStep ? (
                              <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin" />
                            ) : (
                              <Check className="mt-0.5 h-4 w-4 shrink-0" />
                            )}
                            <span>{step}</span>
                          </div>
                        );
                      },
                    )}
                  </div>
                ) : (
                  <div aria-live="polite" className="prose prose-sm prose-slate max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )
              ) : (
                msg.content
              )}

              {/* Rating buttons for AI messages */}
              {msg.role === "ai" && msg.id && msg.content && !msg.isPending && (
                <div
                  className="mt-2 flex items-center gap-2 border-t pt-2"
                  style={{ borderColor: "var(--border)" }}
                >
                  <button
                    onClick={() => rateAnswer(idx, msg.id!, 1)}
                    className={`p-1 rounded transition-colors ${
                      msg.rating === 1
                        ? "text-emerald-500"
                        : "hover:text-emerald-500"
                    }`}
                    style={msg.rating === 1 ? undefined : { color: "var(--text-muted)" }}
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => rateAnswer(idx, msg.id!, -1)}
                    className={`p-1 rounded transition-colors ${
                      msg.rating === -1
                        ? "text-red-400"
                        : "hover:text-red-400"
                    }`}
                    style={msg.rating === -1 ? undefined : { color: "var(--text-muted)" }}
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
        {!hasMessages && suggestions.length > 0 ? (
          <div className="mb-3 flex flex-wrap gap-2">
            {suggestions.slice(0, 1).map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => {
                  void handleSend(suggestion);
                }}
                disabled={streaming}
                className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
                style={{
                  borderColor: "rgba(37,99,235,0.18)",
                  backgroundColor: "rgba(37,99,235,0.06)",
                  color: "var(--text-primary)",
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        ) : null}

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
            aria-busy={streaming}
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
            aria-label={streaming ? "Tutor is replying" : "Send question"}
            onClick={() => {
              void handleSend();
            }}
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
