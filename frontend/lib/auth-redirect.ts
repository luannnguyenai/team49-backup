export function buildUnauthorizedRedirectTarget(currentPath: string): string {
  if (!currentPath) return "/login";
  return `/login?next=${encodeURIComponent(currentPath)}`;
}
