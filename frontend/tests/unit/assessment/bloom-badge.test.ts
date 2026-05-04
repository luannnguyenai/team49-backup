import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(join(process.cwd(), "app/assessment/page.tsx"), "utf8");

describe("Assessment bloom badge contract", () => {
  it("uses bloom token utilities", () => {
    expect(source).toContain("bg-bloom-remember-soft text-bloom-remember");
    expect(source).toContain("bg-bloom-analyze-soft text-bloom-analyze");
    expect(source).not.toMatch(/bg-(sky|violet|amber|rose)-100/);
  });
});
