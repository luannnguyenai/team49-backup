import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "@/components/landing/LandingPage";

describe("Landing CTA contract", () => {
  it("routes primary learning-path CTAs through login", () => {
    render(<LandingPage />);

    const ctaLinks = screen.getAllByRole("link", { name: /get your own learning path/i });
    expect(ctaLinks.length).toBeGreaterThan(0);
    expect(ctaLinks[0]).toHaveAttribute("href", "/login?from=%2Fonboarding");
    expect(ctaLinks[0].className).toContain("btn-primary");
  });

  it("keeps public auth links available in the landing nav", () => {
    render(<LandingPage />);

    expect(screen.getAllByRole("link", { name: /^sign in$/i })[0]).toHaveAttribute("href", "/login");
    expect(screen.getAllByRole("link", { name: /^sign up$/i })[0]).toHaveAttribute("href", "/register");
  });
});
