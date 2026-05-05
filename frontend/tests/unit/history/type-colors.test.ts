import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(join(process.cwd(), "app/(protected)/history/page.tsx"), "utf8");

describe("History token contracts", () => {
  it("uses session tokens for type colors", () => {
    expect(source).toContain("bg-session-assessment-soft text-session-assessment");
    expect(source).toContain("bg-session-quiz-soft text-session-quiz");
    expect(source).not.toMatch(/bg-(violet|blue|amber)-100 text-(violet|blue|amber)-700/);
  });

  it("uses bloom CSS variables for bars", () => {
    expect(source).toContain("var(--bloom-remember)");
    expect(source).toContain("var(--bloom-analyze)");
    expect(source).not.toMatch(/#[0-9a-fA-F]{6}/);
  });
});
