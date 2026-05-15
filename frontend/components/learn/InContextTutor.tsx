"use client";

// components/learn/InContextTutor.tsx
// In-context AI Tutor panel embedded within the learning unit shell.
// Reuses the existing /api/lectures/ask endpoint for Q&A streaming.

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowUp,
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
  TriangleAlert,
  Clock3,
  Bot,
  Check,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
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
  activityStartedAt?: number;
  activityCompletedAt?: number;
}

function formatMessageTime(date: Date): string {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatVideoTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "00:00";
  }

  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  return `${minutes}:${secs.toString().padStart(2, "0")}`;
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

    // Keep browser traffic on the current origin so auth cookies and stream
    // proxying continue to work even when NEXT_PUBLIC_API_URL points elsewhere.
    return "/api/lectures/ask";
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

function formatTutorActivityDuration(ms: number) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

function getTutorActivityHeader({
  startedAt,
  completedAt,
  now,
}: {
  startedAt?: number;
  completedAt?: number;
  now: number;
}) {
  if (!startedAt) {
    return "Thought process";
  }

  const duration = formatTutorActivityDuration((completedAt ?? now) - startedAt);
  return completedAt ? `Thought for ${duration}` : `Thinking · ${duration}`;
}

function TutorActivityCard({
  message,
  isExpanded,
  onToggle,
}: {
  message: ChatMessage;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [now, setNow] = useState(Date.now());
  const steps = getDisplayStatusSteps(message);
  const completed = !message.isPending;
  const currentLine = steps[steps.length - 1] ?? "Preparing request";
  const header = getTutorActivityHeader({
    startedAt: message.activityStartedAt,
    completedAt: message.activityCompletedAt,
    now,
  });

  useEffect(() => {
    if (completed || typeof window === "undefined") return;
    const intervalId = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [completed]);

  return (
    <div className="mb-3 w-full max-w-xl rounded-2xl border border-border-subtle/70 bg-surface-card/55 px-3 py-2.5 text-text-muted shadow-sm backdrop-blur-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={isExpanded}
      >
        <span className="flex min-w-0 items-center gap-2.5">
          <span
            className={cn(
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-surface-page text-primary-700",
              !completed && "border-primary-200 text-primary-700 dark:text-primary-300",
            )}
          >
            {completed ? <Check className="h-3.5 w-3.5" /> : <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-text-body">{header}</span>
            {!completed ? <span className="mt-0.5 block truncate text-xs text-text-muted">{currentLine}</span> : null}
          </span>
        </span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", isExpanded && "rotate-180")} />
      </button>

      {isExpanded ? (
        <div className="mt-3 border-l border-border-subtle pl-4">
          <div className="space-y-3">
            {steps.length > 0 ? (
              steps.map((step, stepIdx) => {
                const isCurrentStep = message.isPending && stepIdx === steps.length - 1;
                const { icon: StepIcon } = getStatusStepMeta(step);

                return (
                  <div key={`${message.localId}-activity-${stepIdx}`} className="relative">
                    <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-text-muted" />
                    <p className="flex items-center gap-2 text-sm font-semibold text-text-body">
                      {isCurrentStep ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-700" />
                      ) : (
                        <StepIcon className="h-3.5 w-3.5 text-text-muted" />
                      )}
                      {step}
                    </p>
                  </div>
                );
              })
            ) : (
              <div className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-text-muted" />
                <p className="text-sm font-semibold text-text-body">Preparing request</p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
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
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
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
    const activityStartedAt = Date.now();

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
      activityStartedAt,
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
                  i === aiIdx
                    ? { ...m, role: "error", content: data.e, isPending: false, activityCompletedAt: Date.now() }
                    : m,
                ),
              );
              hasError = true;
              break;
            }
            if (data.blocked && data.message) {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === aiIdx
                    ? { ...m, role: "error", content: data.message, isPending: false, activityCompletedAt: Date.now() }
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
                    ? { ...m, role: "error", content: String(data.detail), isPending: false, activityCompletedAt: Date.now() }
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
                    i === aiIdx
                      ? { ...m, role: "error", content: data.e, isPending: false, activityCompletedAt: Date.now() }
                      : m,
                  ),
                );
              } else if (data.blocked && data.message) {
                setMessages((prev) =>
                  prev.map((m, i) =>
                    i === aiIdx
                      ? { ...m, role: "error", content: data.message, isPending: false, activityCompletedAt: Date.now() }
                      : m,
                  ),
                );
              } else if (data.detail) {
                setMessages((prev) =>
                  prev.map((m, i) =>
                    i === aiIdx
                      ? { ...m, role: "error", content: String(data.detail), isPending: false, activityCompletedAt: Date.now() }
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
                  activityCompletedAt: Date.now(),
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
                  activityCompletedAt: Date.now(),
                }
              : m,
          ),
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection error";
      setMessages((prev) =>
        prev.map((m, i) =>
          i === aiIdx
            ? { ...m, role: "error", content: msg, senderName: "AI Tutor", isPending: false, activityCompletedAt: Date.now() }
            : m,
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
  const currentVideoTime = formatVideoTime(currentTime);
  const selectedChatModel = CHAT_MODEL_OPTIONS.find((option) => option.id === chatModelId) ?? CHAT_MODEL_OPTIONS[0];

  const toggleStepVisibility = useCallback((localId: string) => {
    setExpandedStepMessageIds((prev) => ({
      ...prev,
      [localId]: !prev[localId],
    }));
  }, []);

  useEffect(() => {
    if (streaming) {
      setIsModelMenuOpen(false);
    }
  }, [streaming]);

  return (
    <div className="flex h-full flex-col bg-surface-page text-text-strong">
      {/* Header */}
      <div
        className="shrink-0 border-b border-border-subtle bg-white/80 px-4 py-3 backdrop-blur dark:bg-slate-950/80"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="hero-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl text-white shadow-brand-soft">
                <Bot className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-text-strong">
                    AI Tutor
                  </span>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                </div>
                <p className="truncate text-xs font-medium text-text-muted">
                  Context-aware help for this unit
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-primary-200 bg-surface-accent-soft px-2.5 py-1 text-[11px] font-medium text-primary-700 dark:text-primary-300"
                title={unitTitle}
              >
                <BookOpenText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{unitTitle}</span>
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-border-subtle px-2.5 py-1 text-[11px] font-medium tabular-nums text-text-muted"
              >
                <Clock3 className="h-3.5 w-3.5" />
                {currentVideoTime}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 items-center">
            {onClose ? (
              <button
                onClick={onClose}
                className="rounded-xl p-2 text-text-muted transition-colors hover:bg-surface-page hover:text-text-strong"
              >
                <span className="sr-only">Close tutor</span>
                <X className="h-4 w-4" />
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {/* Chat messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {!hasMessages && (
          <div className="flex min-h-[360px] flex-col items-center justify-center px-2 py-10 text-center">
            <div className="hero-gradient mb-4 flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-brand-soft">
              <Sparkles className="h-7 w-7" />
            </div>
            <p className="mb-1 text-sm font-semibold text-text-strong">
              Ask anything about this lecture
            </p>
            <p className="max-w-xs text-xs leading-relaxed text-text-muted">
              Your questions are linked to{" "}
              <span className="font-medium">{unitTitle}</span> at the current
              video timestamp.
            </p>
            {suggestions.length > 0 ? (
              <div className="mt-5 flex w-full max-w-[320px] flex-col gap-2">
                {suggestions.slice(0, 3).map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      void handleSend(suggestion);
                    }}
                    disabled={streaming}
                    className="rounded-2xl border border-border-subtle bg-white/80 px-3 py-2 text-left text-xs font-medium leading-snug text-text-strong shadow-sm transition hover:border-primary-200 hover:bg-surface-accent-soft disabled:opacity-50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            ) : null}
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
              const shouldShowTutorActivity = msg.role === "ai" && hasStepHistory;
              const shouldRenderMessageBubble =
                msg.role !== "ai" || Boolean(msg.content) || !shouldShowTutorActivity;
              const shouldShowActiveStatus = false;
              const shouldShowProgressToggle = false;
              const shouldShowLegacyStepList = false;

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

            {shouldShowTutorActivity ? (
              <TutorActivityCard
                message={msg}
                isExpanded={isStepListExpanded}
                onToggle={() => toggleStepVisibility(msg.localId)}
              />
            ) : null}

            {shouldRenderMessageBubble ? (
              <div
              className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                msg.role === "user"
                  ? "rounded-br-md bg-primary-600 text-white shadow-[0_4px_12px_rgba(79,70,229,0.15)]"
                  : msg.role === "error"
                    ? "rounded-bl-md border border-red-200 bg-red-50 text-red-700"
                    : "rounded-bl-md border border-border-subtle bg-surface-card text-text-strong transition-all duration-200"
              }`}
            >
              {msg.role === "ai" ? (
                <>
                  {shouldShowActiveStatus ? (
                    <div
                      aria-live="polite"
                      className="mb-3 space-y-2"
                    >
                      {latestStep ? (
                        <div
                          className="rounded-xl border bg-white/70 px-3 py-2 dark:bg-slate-900/60"
                          style={{ borderColor: "var(--border)" }}
                        >
                          <div className="flex items-start gap-2 italic">
                            {(() => {
                              const { icon: StepIcon, accentClassName } = getStatusStepMeta(latestStep);
                              return msg.isPending ? (
                                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center ${accentClassName}`}>
                                  <Loader2 className="h-4 w-4 animate-spin" />
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
                              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-text-muted transition-colors hover:text-primary-700"
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
                        <div className="flex items-center gap-2 text-text-muted">
                          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                        </div>
                      )}
                    </div>
                  ) : null}

                  {shouldShowProgressToggle ? (
                    <button
                      type="button"
                      onClick={() => toggleStepVisibility(msg.localId)}
                      className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-text-muted transition-colors hover:text-primary-700"
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

                  {shouldShowLegacyStepList && hasStepHistory && isStepListExpanded ? (
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
                    aria-label="Useful"
                    title="Useful"
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
                    aria-label="Not Useful"
                    title="Not Useful"
                    className={`p-1 rounded transition-colors ${
                      msg.rating === -1
                        ? "text-red-400"
                        : "hover:text-red-400"
                    }`}
                    style={msg.rating === -1 ? undefined : { color: "var(--text-muted)" }}
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    aria-label="Report to admin"
                    title="Report to admin"
                    className="ml-auto rounded p-1 text-amber-500 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-500/10"
                  >
                    <TriangleAlert className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
            ) : null}
                </>
              );
            })()}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div
        className="shrink-0 border-t border-border-subtle bg-surface-page/80 p-3 backdrop-blur"
      >
        <div className="overflow-visible rounded-2xl border border-border-subtle bg-surface-card shadow-[0_1px_8px_rgba(0,0,0,0.03)] transition-colors focus-within:border-primary-200">
          <textarea
            ref={inputRef}
            rows={1}
            aria-busy={streaming}
            className="max-h-[160px] min-h-[52px] w-full resize-none bg-transparent px-4 pb-2 pt-3.5 text-[15px] leading-relaxed text-text-strong outline-none placeholder:text-text-muted"
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
          <div className="flex items-center justify-between gap-2 border-t border-border-subtle/35 px-3 py-2">
            <div
              className="relative"
              onBlur={(event) => {
                const nextFocus = event.relatedTarget as Node | null;
                if (!event.currentTarget.contains(nextFocus)) {
                  setIsModelMenuOpen(false);
                }
              }}
            >
              <button
                type="button"
                disabled={streaming}
                onClick={() => setIsModelMenuOpen((open) => !open)}
                className="inline-flex h-[29px] max-w-[150px] items-center gap-1.5 rounded-full border border-primary-200 bg-surface-accent-soft px-2.5 text-[11px] font-medium text-primary-700 transition hover:border-primary-300 disabled:cursor-not-allowed disabled:opacity-60 dark:text-primary-300"
                aria-label={`Tutor model: ${selectedChatModel.label}`}
                aria-expanded={isModelMenuOpen}
                aria-haspopup="menu"
              >
                <Bot className="h-3 w-3 shrink-0" />
                <span className="truncate">{selectedChatModel.label}</span>
                <ChevronDown
                  className={cn(
                    "h-3 w-3 shrink-0 transition-transform",
                    isModelMenuOpen && "rotate-180",
                  )}
                />
              </button>
              {isModelMenuOpen ? (
                <div
                  role="menu"
                  className="absolute bottom-full left-0 z-30 mb-2 w-56 overflow-hidden rounded-xl border border-border-subtle bg-surface-card p-1.5 shadow-[0_12px_32px_rgba(15,23,42,0.14)]"
                >
                  {CHAT_MODEL_OPTIONS.map((option) => {
                    const availability = getChatModelAvailability(chatModelAvailability, option.id);
                    const isActive = chatModelId === option.id;
                    const isUnavailable = !availability.available;
                    const statusLabel = isUnavailable ? availability.status : null;
                    return (
                      <button
                        key={option.id}
                        type="button"
                        role="menuitemradio"
                        disabled={streaming || isUnavailable}
                        aria-checked={isActive}
                        onClick={() => {
                          changeChatModel(option.id);
                          setIsModelMenuOpen(false);
                        }}
                        title={isUnavailable ? `${option.label} is ${availability.status}` : option.label}
                        className={cn(
                          "flex min-h-9 w-full items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
                          isActive
                            ? "bg-surface-accent-soft text-primary-700 dark:text-primary-300"
                            : "text-text-muted hover:bg-surface-page hover:text-text-strong",
                        )}
                      >
                        <Bot className="h-3.5 w-3.5 shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{option.label}</span>
                        {statusLabel ? (
                          <span className="shrink-0 rounded-full bg-rose-500/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-rose-700 dark:text-rose-300">
                            {statusLabel}
                          </span>
                        ) : null}
                        {isActive ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
            <button
              aria-label={streaming ? "Tutor is replying" : "Send question"}
              onClick={() => {
                void handleSend();
              }}
              disabled={streaming || !input.trim()}
              className="flex h-[29px] w-[29px] shrink-0 items-center justify-center rounded-full bg-primary-600 p-0 text-white shadow-[0_4px_12px_rgba(79,70,229,0.15)] transition hover:shadow-[0_6px_16px_rgba(79,70,229,0.22)] disabled:cursor-not-allowed disabled:opacity-25 disabled:shadow-none"
            >
              {streaming ? (
                <Loader2 className="h-[15px] w-[15px] animate-spin" />
              ) : (
                <ArrowUp className="h-[15px] w-[15px]" strokeWidth={2.5} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
