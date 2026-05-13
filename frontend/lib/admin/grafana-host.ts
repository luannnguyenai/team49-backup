function normalizeGrafanaPath(pathname: string): string {
  const normalized = pathname.trim().replace(/\/+$/, "");
  return normalized || "/grafana";
}

export function resolveGrafanaBaseUrl(
  configuredHost: string | undefined,
  currentOrigin?: string,
): { baseUrl: string; warning: string | null } {
  const trimmed = configuredHost?.trim() ?? "";
  if (!trimmed) {
    return { baseUrl: "/grafana", warning: null };
  }

  if (trimmed.startsWith("/")) {
    return { baseUrl: normalizeGrafanaPath(trimmed), warning: null };
  }

  try {
    const configured = new URL(trimmed);
    const configuredPath = normalizeGrafanaPath(configured.pathname);
    if (!currentOrigin) {
      return { baseUrl: `${configured.origin}${configuredPath}`, warning: null };
    }

    const current = new URL(currentOrigin);
    if (configured.host === current.host) {
      return { baseUrl: configuredPath, warning: null };
    }

    if (current.protocol === "https:" && configured.protocol === "http:") {
      return {
        baseUrl: "/grafana",
        warning:
          "Configured Grafana host is HTTP while the admin app is HTTPS. Falling back to same-origin /grafana for embedding.",
      };
    }

    return { baseUrl: `${configured.origin}${configuredPath}`, warning: null };
  } catch {
    return {
      baseUrl: "/grafana",
      warning:
        "Configured Grafana host is invalid. Falling back to same-origin /grafana for embedding.",
    };
  }
}
