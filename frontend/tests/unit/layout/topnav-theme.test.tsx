import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PublicTopNav from "@/components/layout/PublicTopNav";

describe("PublicTopNav theme contract", () => {
  it("keeps a translucent shell and a strong primary CTA", () => {
    render(<PublicTopNav />);

    expect(screen.getByRole("banner").className).toMatch(/backdrop-blur/);
    expect(screen.getByRole("link", { name: /sign up/i }).className).toMatch(
      /bg-slate-950|btn-primary/,
    );
  });
});
