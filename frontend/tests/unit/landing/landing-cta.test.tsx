import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "@/components/landing/LandingPage";

describe("Landing CTA contract", () => {
  it("uses shared primary and secondary button utilities", () => {
    render(<LandingPage />);

    const createLinks = screen.getAllByRole("link", { name: /create your account/i });
    expect(createLinks[0].className).toContain("btn-primary");
    expect(createLinks[0].className).not.toMatch(/\bbg-slate-950\b/);

    const signInLinks = screen.getAllByRole("link", { name: /^sign in$/i });
    expect(signInLinks[0].className).toContain("btn-secondary");
  });
});
