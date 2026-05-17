const DEFAULT_LEARN_HREF = "/learn";
const FLOW_ROUTE_PREFIXES = ["/onboarding", "/assessment"];

function normalizeNextHref(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) {
    return DEFAULT_LEARN_HREF;
  }

  try {
    const url = new URL(next, "https://vinlearn.local");
    const isFlowRoute = FLOW_ROUTE_PREFIXES.some(
      (prefix) => url.pathname === prefix || url.pathname.startsWith(`${prefix}/`),
    );

    if (isFlowRoute) {
      return DEFAULT_LEARN_HREF;
    }

    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return DEFAULT_LEARN_HREF;
  }
}

export function buildAssessmentNextHref(next: string | null): string {
  return normalizeNextHref(next);
}

export function buildPostOnboardingHref({
  hasAssessmentUnits,
  requestedNext,
}: {
  hasAssessmentUnits: boolean;
  requestedNext: string | null;
}): string {
  const nextHref = normalizeNextHref(requestedNext);

  if (!hasAssessmentUnits) {
    return nextHref;
  }

  return `/assessment?next=${encodeURIComponent(nextHref)}`;
}
