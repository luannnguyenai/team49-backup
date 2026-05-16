import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { middleware } from "@/middleware";

describe("auth middleware public route handling", () => {
  it("allows unauthenticated forgot-password route", () => {
    const request = new NextRequest("http://localhost:3000/forgot-password");

    const response = middleware(request);

    expect(response.status).toBe(200);
  });

  it("allows unauthenticated reset-password route", () => {
    const request = new NextRequest("http://localhost:3000/reset-password?token=abc");

    const response = middleware(request);

    expect(response.status).toBe(200);
  });

  it("allows authenticated forgot-password route", () => {
    const request = new NextRequest("http://localhost:3000/forgot-password");
    request.cookies.set("al_access_token", "token");

    const response = middleware(request);

    expect(response.status).toBe(200);
  });

  it("preserves redirect query strings when an authenticated user lands on an auth page", () => {
    const request = new NextRequest(
      "http://localhost:3000/login?next=%2Fassessment%3Fnext%3D%252Fdashboard",
    );
    request.cookies.set("al_access_token", "token");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/assessment?next=%2Fdashboard",
    );
  });

  it("falls back to dashboard for unsafe authenticated auth redirects", () => {
    const request = new NextRequest("http://localhost:3000/login?next=%2F%2Fevil.example");
    request.cookies.set("al_access_token", "token");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });

  it("redirects unauthenticated app routes to the landing page", () => {
    const request = new NextRequest("http://localhost:3000/learn");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("redirects unauthenticated course routes to the landing page", () => {
    const request = new NextRequest("http://localhost:3000/courses/cs231n");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("redirects authenticated users away from the public landing page", () => {
    const request = new NextRequest("http://localhost:3000/");
    request.cookies.set("al_access_token", "token");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/agent");
  });
});
