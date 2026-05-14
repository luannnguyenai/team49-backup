export type ChatModelId = "default" | "qwen35_4b";

export const CHAT_MODEL_OPTIONS: Array<{ id: ChatModelId; label: string }> = [
  { id: "default", label: "Auto" },
  { id: "qwen35_4b", label: "Qwen 3.5 4B" },
];

export type ChatModelAvailability = {
  id: string;
  label: string;
  status: string;
  available: boolean;
  checkedAt?: string | null;
  checked_at?: string | null;
  user_selectable?: boolean;
};

export type ChatModelAvailabilityResponse = {
  models: ChatModelAvailability[];
};

export const DEFAULT_CHAT_MODEL_AVAILABILITY: ChatModelAvailability[] = CHAT_MODEL_OPTIONS.map((option) => ({
  ...option,
  status: "unknown",
  available: true,
}));

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

export function normalizeChatModelAvailability(
  models: ChatModelAvailability[] | undefined | null,
): ChatModelAvailability[] {
  if (!models?.length) return DEFAULT_CHAT_MODEL_AVAILABILITY;
  const byId = new Map(
    models
      .filter((model): model is ChatModelAvailability => isChatModelId(model?.id))
      .map((model) => [
        model.id,
        {
          ...model,
          label: model.label || CHAT_MODEL_OPTIONS.find((option) => option.id === model.id)?.label || model.id,
          available: model.available !== false && model.status !== "down",
        },
      ]),
  );
  const selectable = CHAT_MODEL_OPTIONS.map((option) => byId.get(option.id) ?? { ...option, status: "unknown", available: true });
  const nonSelectable = models.filter((model) => !isChatModelId(model?.id) && model.user_selectable === false);
  return [...selectable, ...nonSelectable];
}

export function getChatModelAvailability(
  models: ChatModelAvailability[],
  modelId: ChatModelId,
): ChatModelAvailability {
  return (
    models.find((model) => model.id === modelId) ??
    DEFAULT_CHAT_MODEL_AVAILABILITY.find((model) => model.id === modelId) ??
    DEFAULT_CHAT_MODEL_AVAILABILITY[0]
  );
}

export function isChatModelAvailable(models: ChatModelAvailability[], modelId: ChatModelId): boolean {
  return getChatModelAvailability(models, modelId).available;
}

export function fallbackUnavailableChatModel(
  models: ChatModelAvailability[],
  modelId: ChatModelId,
): ChatModelId {
  return isChatModelAvailable(models, modelId) ? modelId : "default";
}

export async function fetchChatModelAvailability(): Promise<ChatModelAvailability[]> {
  const response = await fetch("/api/chat-models/availability", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`model availability request failed (${response.status})`);
  }
  const payload = (await response.json()) as ChatModelAvailabilityResponse;
  return normalizeChatModelAvailability(payload.models);
}
