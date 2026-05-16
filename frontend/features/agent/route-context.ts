export interface AgentRouteContextSnapshot {
  route: string;
  courseSlug?: string;
  unitSlug?: string;
  canonicalUnitId?: string;
  playerTimestampSec?: number;
  savedAt: number;
}

export const AGENT_ROUTE_CONTEXT_STORAGE_KEY = "agent.routeContext";
const ROUTE_CONTEXT_TTL_MS = 2 * 60 * 60 * 1000;

function cleanString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function cleanTimestamp(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? Math.round(value)
    : undefined;
}

function normalizeSnapshot(
  value: Partial<AgentRouteContextSnapshot>,
): AgentRouteContextSnapshot | null {
  const route = cleanString(value.route);
  if (!route) return null;

  return {
    route,
    courseSlug: cleanString(value.courseSlug),
    unitSlug: cleanString(value.unitSlug),
    canonicalUnitId: cleanString(value.canonicalUnitId),
    playerTimestampSec: cleanTimestamp(value.playerTimestampSec),
    savedAt: cleanTimestamp(value.savedAt) ?? Date.now(),
  };
}

export function writeAgentRouteContext(
  value: Partial<AgentRouteContextSnapshot>,
): void {
  if (typeof window === "undefined") return;
  const snapshot = normalizeSnapshot(value);
  if (!snapshot) return;
  window.localStorage.setItem(
    AGENT_ROUTE_CONTEXT_STORAGE_KEY,
    JSON.stringify(snapshot),
  );
}

export function readAgentRouteContext(): Record<string, unknown> | undefined {
  if (typeof window === "undefined") return undefined;
  const raw = window.localStorage.getItem(AGENT_ROUTE_CONTEXT_STORAGE_KEY);
  if (!raw) return undefined;

  try {
    const snapshot = normalizeSnapshot(JSON.parse(raw));
    if (!snapshot) return undefined;
    if (Date.now() - snapshot.savedAt > ROUTE_CONTEXT_TTL_MS) return undefined;

    const routeContext: Record<string, unknown> = {
      route: snapshot.route,
    };
    if (snapshot.courseSlug) routeContext.courseSlug = snapshot.courseSlug;
    if (snapshot.unitSlug) routeContext.unitSlug = snapshot.unitSlug;
    if (snapshot.canonicalUnitId) routeContext.canonicalUnitId = snapshot.canonicalUnitId;
    if (snapshot.playerTimestampSec !== undefined) {
      routeContext.playerTimestampSec = snapshot.playerTimestampSec;
    }
    return routeContext;
  } catch {
    return undefined;
  }
}
