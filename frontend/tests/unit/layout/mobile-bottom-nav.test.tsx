import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MobileBottomNav from "@/components/layout/MobileBottomNav";

describe("MobileBottomNav", () => {
  it("renders the protected primary destinations in the configured priority order", () => {
    render(<MobileBottomNav pathname="/learn" />);

    expect(screen.getAllByRole("link").map((link) => link.textContent?.trim())).toEqual([
      "Dashboard",
      "Learn",
      "AI Assistant",
      "History",
      "Profile",
    ]);
    expect(screen.getByRole("link", { name: "Learn" })).toHaveAttribute("aria-current", "page");
  });
});
