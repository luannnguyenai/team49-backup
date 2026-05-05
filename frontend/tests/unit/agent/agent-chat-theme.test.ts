import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(join(process.cwd(), "features/agent/components/AgentChatPage.tsx"), "utf8");

describe("Agent chat theme contract", () => {
  it("uses shared landing theme utilities for the copilot shell and composer", () => {
    expect(source).toContain("AI Learning Copilot");
    expect(source).toContain("hero-gradient");
    expect(source).toContain("card-glass");
    expect(source).toContain("btn-primary");
    expect(source).toContain("btn-secondary");
    expect(source).toContain("input-base");
  });

  it("does not reintroduce raw blue/slate visual treatments for agent UI controls", () => {
    expect(source).not.toMatch(/\b(bg|text|border|hover:bg|hover:border|focus:border|focus:ring)-blue-/);
    expect(source).not.toContain("font-black");
  });
});
