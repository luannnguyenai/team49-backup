import { describe, expect, it } from "vitest";

import { resolveGrafanaBaseUrl } from "@/lib/admin/grafana-host";

describe("resolveGrafanaBaseUrl", () => {
  it("falls back to the same-origin grafana path when the env var is empty", () => {
    expect(resolveGrafanaBaseUrl("", "https://app.example.com")).toEqual({
      baseUrl: "/grafana",
      warning: null,
    });
  });

  it("keeps relative grafana paths as-is", () => {
    expect(resolveGrafanaBaseUrl("/grafana/", "https://app.example.com")).toEqual({
      baseUrl: "/grafana",
      warning: null,
    });
  });

  it("falls back to the same-origin grafana path when an insecure http host would be embedded inside https", () => {
    expect(
      resolveGrafanaBaseUrl(
        "http://a20-prod-alb-1105228802.ap-southeast-1.elb.amazonaws.com/grafana",
        "https://app.example.com",
      ),
    ).toEqual({
      baseUrl: "/grafana",
      warning: "Configured Grafana host is HTTP while the admin app is HTTPS. Falling back to same-origin /grafana for embedding.",
    });
  });

  it("uses the configured https host when cross-origin embedding is safe", () => {
    expect(resolveGrafanaBaseUrl("https://metrics.example.com/grafana/", "https://app.example.com"))
      .toEqual({
        baseUrl: "https://metrics.example.com/grafana",
        warning: null,
      });
  });

  it("normalizes same-host absolute URLs back to same-origin paths", () => {
    expect(resolveGrafanaBaseUrl("https://app.example.com/grafana/", "https://app.example.com")).toEqual({
      baseUrl: "/grafana",
      warning: null,
    });
  });
});
