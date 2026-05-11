"use client";

// components/learn/InContextTutor.tsx
// In-context AI Tutor panel embedded within the learning unit shell.
// Reuses the existing /api/lectures/ask endpoint for Q&A streaming.

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  Send,
  X,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  ChevronDown,
  ChevronUp,
  BookOpenText,
  Search,
  Brain,
  Calculator,
  RefreshCw,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  CHAT_MODEL_OPTIONS,
  CHAT_MODEL_STORAGE_KEYS,
  DEFAULT_CHAT_MODEL_AVAILABILITY,
  fallbackUnavailableChatModel,
  fetchChatModelAvailability,
  getChatModelAvailability,
  isChatModelAvailable,
  readStoredChatModelId,
  writeStoredChatModelId,
  type ChatModelAvailability,
  type ChatModelId,
} from "@/lib/chat-model-options";
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

function getTutorAskUrl(): string {
  if (typeof window === "undefined") {
    return "/api/lectures/ask";
  }

  const configuredApiBase = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!configuredApiBase) {
    return "/api/lectures/ask";
  }

  try {
    const normalizedBase = configuredApiBase.endsWith("/")
      ? configuredApiBase
      : `${configuredApiBase}/`;
    const directUrl = new URL("api/lectures/ask", normalizedBase);

    if (directUrl.origin === window.location.origin) {
      return directUrl.pathname;
    }

    return directUrl.toString();
  } catch {
    return "/api/lectures/ask";
  }
}

const MIN_STATUS_VISIBLE_MS = 450;

const LEGACY_STATUS_LABELS: Record<string, string> = {
  "Đang đọc ngữ cảnh bài giảng...": "Reading lecture context...",
  "Đang tìm phần nội dung liên quan...": "Finding the most relevant section...",
  "Đang suy nghĩ câu trả lời...": "Thinking through the answer...",
  "Đang kiểm tra phép tính...": "Checking the calculation...",
  "Đang thử lại phép tính...": "Retrying the calculation...",
  "Đang hoàn thiện câu trả lời...": "Finalizing the answer...",
};

function normalizeTutorStatusLabel(status: string): string {
  const trimmed = status.trim();
  if (!trimmed) {
    return trimmed;
  }

  return LEGACY_STATUS_LABELS[trimmed] ?? trimmed;
}

function getStatusStepMeta(status: string): {
  icon: LucideIcon;
  accentClassName: string;
} {
  const normalizedStatus = normalizeTutorStatusLabel(status);

  switch (normalizedStatus) {
    case "Reading lecture context...":
      return { icon: BookOpenText, accentClassName: "text-sky-500" };
    case "Finding the most relevant section...":
      return { icon: Search, accentClassName: "text-indigo-500" };
    case "Thinking through the answer...":
      return { icon: Brain, accentClassName: "text-fuchsia-500" };
    case "Checking the calculation...":
      return { icon: Calculator, accentClassName: "text-emerald-500" };
    case "Retrying the calculation...":
      return { icon: RefreshCw, accentClassName: "text-amber-500" };
    case "Finalizing the answer...":
      return { icon: Sparkles, accentClassName: "text-rose-500" };
    default:
      return { icon: Sparkles, accentClassName: "text-blue-500" };
  }
}

function appendStatusStep(steps: string[] | undefined, nextStatus: string): string[] {
  const normalizedStatus = normalizeTutorStatusLabel(nextStatus);
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

function getDisplayStatusSteps(message: ChatMessage): string[] {
  if (message.statusSteps?.length) {
    return message.statusSteps.map(normalizeTutorStatusLabel);
  }

  if (message.statusText) {
    return [normalizeTutorStatusLabel(message.statusText)];
  }

  return [];
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
  const [chatModelId, setChatModelId] = useState<ChatModelId>("default");
  const [chatModelAvailability, setChatModelAvailability] = useState<ChatModelAvailability[]>(
    DEFAULT_CHAT_MODEL_AVAILABILITY,
  );
  const [expandedStepMessageIds, setExpandedStepMessageIds] = useState<Record<string, boolean>>({});
  const userFullName = useAuthStore((state) => state.user?.full_name?.trim() || "You");
  const resolvedLessonKey = lessonKey?.trim() || lectureId.trim();
  const conversationKey = resolvedLessonKey
    ? buildTutorConversationKey(resolvedLessonKey, contextBindingId)
    : null;

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messageIdRef = useRef(0);
  const loadedConversationKeyRef = useRef<string | null>(null);

  useEffect(() => {
    setChatModelId(readStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.tutor));
  }, []);

  useEffect(() => {
    let active = true;
    fetchChatModelAvailability()
      .then((models) => {
        if (!active) return;
        setChatModelAvailability(models);
        setChatModelId((current) => {
          const next = fallbackUnavailableChatModel(models, current);
          if (next !== current) {
            writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.tutor, next);
          }
          return next;
        });
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const changeChatModel = useCallback((modelId: ChatModelId) => {
    if (!isChatModelAvailable(chatModelAvailability, modelId)) return;
    setChatModelId(modelId);
    writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.tutor, modelId);
  }, [chatModelAvailability]);

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
      .map(({ id, role, content, senderName, sentAt, rating, statusSteps }) => ({
        statusSteps: role === "ai" ? statusSteps ?? [] : [],
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
      statusSteps: message.statusSteps ?? [],
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
    const safeChatModelId = fallbackUnavailableChatModel(chatModelAvailability, chatModelId);
    if (safeChatModelId !== chatModelId) {
      setChatModelId(safeChatModelId);
      writeStoredChatModelId(CHAT_MODEL_STORAGE_KEYS.tutor, safeChatModelId);
    }
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
      const resp = await fetch(getTutorAskUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lecture_id: lectureId,
          current_timestamp: currentTime,
          question: q,
          context_binding_id: contextBindingId,
          image_base64: img,
          chatModelId: safeChatModelId,
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
                        isPending: true,
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
                        isPending: true,
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
                            isPending: true,
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
                            isPending: true,
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
          prev.map((m, i) =>
            i === aiIdx
              ? {
                  ...m,
                  id: qaId,
                  isPending: false,
                  statusText: null,
                }
              : m,
          ),
        );
      } else {
        setMessages((prev) =>
          prev.map((m, i) =>
            i === aiIdx
              ? {
                  ...m,
                  isPending: false,
                  statusText: null,
                }
              : m,
          ),
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
  }, [input, streaming, lectureId, currentTime, contextBindingId, messages.length, captureFrame, nextMessageId, userFullName, chatModelId, chatModelAvailability]);

  const hasMessages = messages.length > 0;

  const toggleStepVisibility = useCallback((localId: string) => {
    setExpandedStepMessageIds((prev) => ({
      ...prev,
      [localId]: !prev[localId],
    }));
  }, []);

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
        <div className="flex items-center gap-2">
          <label htmlFor="tutor-model-select" className="sr-only">
            Tutor model
          </label>
          <select
            id="tutor-model-select"
            aria-label="Tutor model"
            value={chatModelId}
            disabled={streaming}
            onChange={(event) => changeChatModel(event.target.value as ChatModelId)}
            className="h-8 rounded-lg border bg-transparent px-2 text-xs font-medium outline-none transition-colors disabled:opacity-60"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-primary)",
            }}
          >
            {CHAT_MODEL_OPTIONS.map((option) => {
              const availability = getChatModelAvailability(chatModelAvailability, option.id);
              const isUnavailable = !availability.available;
              return (
                <option key={option.id} value={option.id} disabled={isUnavailable}>
                  {isUnavailable ? `${option.label} (${availability.status})` : option.label}
                </option>
              );
            })}
          </select>
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
            {(() => {
              const displayStatusSteps = getDisplayStatusSteps(msg);
              const hasStepHistory = displayStatusSteps.length > 0;
              const isStepListExpanded = Boolean(expandedStepMessageIds[msg.localId]);
              const latestStep = hasStepHistory ? displayStatusSteps[displayStatusSteps.length - 1] : null;

              return (
                <>
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
                <>
                  {(msg.isPending || hasStepHistory) ? (
                    <div
                      aria-live="polite"
                      className="mb-3 space-y-2"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {latestStep ? (
                        <div className="rounded-xl border px-3 py-2" style={{ borderColor: "var(--border)" }}>
                          <div className="flex items-start gap-2 italic">
                            {(() => {
                              const { icon: StepIcon, accentClassName } = getStatusStepMeta(latestStep);
                              return msg.isPending ? (
                                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center ${accentClassName}`}>
                                  <StepIcon className="h-4 w-4" />
                                </span>
                              ) : (
                                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center ${accentClassName}`}>
                                  <StepIcon className="h-4 w-4" />
                                </span>
                              );
                            })()}
                            <span>{latestStep}</span>
                          </div>
                          {hasStepHistory ? (
                            <button
                              type="button"
                              onClick={() => toggleStepVisibility(msg.localId)}
                              className="mt-2 inline-flex items-center gap-1 text-xs font-medium transition-colors hover:text-blue-600"
                              style={{ color: "var(--text-muted)" }}
                            >
                              {isStepListExpanded ? (
                                <>
                                  <ChevronUp className="h-3.5 w-3.5" />
                                  Hide progress
                                </>
                              ) : (
                                <>
                                  <ChevronDown className="h-3.5 w-3.5" />
                                  View progress
                                </>
                              )}
                            </button>
                          ) : null}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
                          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                        </div>
                      )}
                    </div>
                  ) : null}

                  {hasStepHistory && isStepListExpanded ? (
                    <div
                      className="mb-3 space-y-2 rounded-xl border px-3 py-3 italic"
                      style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                    >
                      {displayStatusSteps.map((step, stepIdx) => {
                        const isCurrentStep = msg.isPending && stepIdx === displayStatusSteps.length - 1;
                        const { icon: StepIcon, accentClassName } = getStatusStepMeta(step);

                        return (
                          <div
                            key={`${msg.localId}-status-${stepIdx}`}
                            className="flex items-start gap-2"
                            style={{
                              color: isCurrentStep ? "var(--text-secondary)" : "var(--text-muted)",
                            }}
                          >
                            <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center ${accentClassName}`}>
                              {isCurrentStep ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <StepIcon className="h-4 w-4" />
                              )}
                            </span>
                            <span>{step}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}

                  {msg.content ? (
                    <div aria-live="polite" className="prose prose-sm prose-slate max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : msg.isPending ? null : (
                    <div aria-live="polite" className="prose prose-sm prose-slate max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </>
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
                </>
              );
            })()}
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
