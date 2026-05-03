import { describe, expect, it } from "vitest";

import { metadata as rootMetadata } from "@/app/layout";
import { metadata as homeMetadata } from "@/app/page";

describe("root app metadata", () => {
  it("uses the AI Learning Hub title template for browser tabs", () => {
    expect(rootMetadata.title).toEqual({
      default: "AI Learning Hub",
      template: "AI Learning Hub - %s",
    });
  });

  it("uses a page name title for the landing route instead of the marketing headline", () => {
    expect(homeMetadata.title).toEqual({
      absolute: "AI Learning Hub - Home",
    });
  });
});
