import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(join(process.cwd(), "app/(protected)/profile/page.tsx"), "utf8");

describe("Profile achievement tier contract", () => {
  it("uses tier token utilities", () => {
    expect(source).toContain("border-tier-bronze bg-tier-bronze-soft");
    expect(source).toContain("border-tier-platinum bg-tier-platinum-soft");
    expect(source).not.toMatch(/border-(blue|emerald|yellow|violet)-400/);
  });
});
