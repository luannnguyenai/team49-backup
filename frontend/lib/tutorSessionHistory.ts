export const TUTOR_SESSION_HISTORY_STORAGE_KEY = "al-tutor-session-history";

export interface StoredTutorMessage {
  id?: number;
  role: "user" | "ai" | "error";
  content: string;
  senderName: string;
  sentAt: string;
  rating?: number | null;
}

export function buildTutorConversationKey(
  lectureId: string,
  contextBindingId?: string,
): string {
  return `${lectureId}::${contextBindingId ?? "__lecture__"}`;
}

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

function readHistoryMap(): Record<string, StoredTutorMessage[]> {
  if (!canUseSessionStorage()) {
    return {};
  }

  const raw = window.sessionStorage.getItem(TUTOR_SESSION_HISTORY_STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, StoredTutorMessage[]>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeHistoryMap(historyMap: Record<string, StoredTutorMessage[]>): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(
    TUTOR_SESSION_HISTORY_STORAGE_KEY,
    JSON.stringify(historyMap),
  );
}

export function loadTutorConversation(
  conversationKey: string,
): StoredTutorMessage[] {
  return readHistoryMap()[conversationKey] ?? [];
}

export function saveTutorConversation(
  conversationKey: string,
  messages: StoredTutorMessage[],
): void {
  const historyMap = readHistoryMap();

  if (messages.length === 0) {
    delete historyMap[conversationKey];
  } else {
    historyMap[conversationKey] = messages;
  }

  writeHistoryMap(historyMap);
}

export function clearTutorSessionHistory(): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(TUTOR_SESSION_HISTORY_STORAGE_KEY);
}
