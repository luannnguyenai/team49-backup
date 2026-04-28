const DEFAULT_LEARN_HREF = "/learn";

function normalizeNextHref(next: string | null): string {
  return next && next.startsWith("/") ? next : DEFAULT_LEARN_HREF;
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
