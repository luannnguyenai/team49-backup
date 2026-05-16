export function isSafeInternalRedirectTarget(value: string | null): value is string {
  return Boolean(value && value.startsWith("/") && !value.startsWith("//"));
}

export function getSafeInternalRedirectTarget(
  value: string | null,
  fallback: string,
): string {
  return isSafeInternalRedirectTarget(value) ? value : fallback;
}

export function buildUnauthorizedRedirectTarget(currentPath: string): string {
  if (!currentPath) return "/login";
  return `/login?next=${encodeURIComponent(currentPath)}`;
}
