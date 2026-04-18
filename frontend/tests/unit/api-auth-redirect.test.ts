import { describe, expect, it } from "vitest";

import { buildUnauthorizedRedirectTarget } from "@/lib/auth-redirect";

describe("buildUnauthorizedRedirectTarget", () => {
  it("preserves the current protected path as next", () => {
    expect(buildUnauthorizedRedirectTarget("/courses/cs231n/start")).toBe(
      "/login?next=%2Fcourses%2Fcs231n%2Fstart",
    );
  });

  it("preserves search params in the next redirect", () => {
    expect(
      buildUnauthorizedRedirectTarget(
        "/assessment?next=%2Fcourses%2Fcs231n%2Fstart",
      ),
    ).toBe("/login?next=%2Fassessment%3Fnext%3D%252Fcourses%252Fcs231n%252Fstart");
  });

  it("falls back to plain login when the current path is empty", () => {
    expect(buildUnauthorizedRedirectTarget("")).toBe("/login");
  });
});
