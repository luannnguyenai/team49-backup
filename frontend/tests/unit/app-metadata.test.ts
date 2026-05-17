import { describe, expect, it } from "vitest";

import { metadata as rootMetadata } from "@/app/layout";
import { metadata as homeMetadata } from "@/app/page";

describe("root app metadata", () => {
  it("uses the VinLearn title template for browser tabs", () => {
    expect(rootMetadata.title).toEqual({
      default: "VinLearn",
      template: "VinLearn - %s",
    });
  });

  it("uses a page name title for the landing route instead of the marketing headline", () => {
    expect(homeMetadata.title).toEqual({
      absolute: "VinLearn - Home",
    });
  });
});
