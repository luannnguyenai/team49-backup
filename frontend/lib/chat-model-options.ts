export type ChatModelId = "default" | "qwen35_4b";

export const CHAT_MODEL_OPTIONS: Array<{ id: ChatModelId; label: string }> = [
  { id: "default", label: "Default" },
  { id: "qwen35_4b", label: "Qwen 3.5 4B" },
];

export const CHAT_MODEL_STORAGE_KEYS = {
  agent: "agent.chatModelId",
  tutor: "tutor.chatModelId",
} as const;

export function isChatModelId(value: string | null | undefined): value is ChatModelId {
  return value === "default" || value === "qwen35_4b";
}

export function readStoredChatModelId(key: string, fallback: ChatModelId = "default"): ChatModelId {
  if (typeof window === "undefined") return fallback;
  try {
    const stored = window.localStorage.getItem(key);
    return isChatModelId(stored) ? stored : fallback;
  } catch {
    return fallback;
  }
}

export function writeStoredChatModelId(key: string, value: ChatModelId) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value);
  } catch {}
}
