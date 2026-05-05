import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("Decorative tokens are wired in Tailwind class names", () => {
  it("accepts bloom, session, tier, insight, state, stat and chart utility class names", () => {
    const { container } = render(
      <>
        <div className="bg-bloom-remember-soft text-bloom-remember" />
        <div className="bg-session-quiz-soft text-session-quiz" />
        <div className="border-tier-gold bg-tier-gold-soft" />
        <div className="bg-insight-soft text-insight border-insight-border" />
        <div className="bg-state-success-bg text-state-success-fg" />
        <div className="bg-stat-courses-soft text-stat-courses" />
        <div className="bg-chart-1" />
      </>,
    );

    expect(container.children).toHaveLength(7);
  });
});
