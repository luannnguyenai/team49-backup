import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { middleware } from "@/middleware";

describe("auth middleware public route handling", () => {
  it("allows unauthenticated forgot-password route", () => {
    const request = new NextRequest("http://localhost:3000/forgot-password");

    const response = middleware(request);

    expect(response.status).toBe(200);
  });

  it("redirects authenticated forgot-password route away from auth pages", () => {
    const request = new NextRequest("http://localhost:3000/forgot-password");
    request.cookies.set("al_access_token", "token");

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toContain("/dashboard");
  });
});
