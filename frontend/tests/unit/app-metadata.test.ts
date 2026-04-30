import { describe, expect, it } from "vitest";

import { metadata as rootMetadata } from "@/app/layout";

describe("root app metadata", () => {
  it("uses the AI Learning Hub title template for browser tabs", () => {
    expect(rootMetadata.title).toEqual({
      default: "AI Learning Hub",
      template: "AI Learning Hub - %s",
    });
  });
});
