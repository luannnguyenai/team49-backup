import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PathItemResponse } from "@/types";
import LearningUnitDrawer from "@/features/learning-path/components/LearningUnitDrawer";
import { useLearningPathStore } from "@/features/learning-path/store";

vi.mock("@/lib/api", () => ({
  learningUnitApi: {
    contentById: vi.fn(() => new Promise(() => {})),
  },
}));

function pathItem(overrides: Partial<PathItemResponse> = {}): PathItemResponse {
  return {
    id: overrides.id ?? "path-item-1",
    learning_unit_id: overrides.learning_unit_id ?? "unit-1",
    learning_unit_title: overrides.learning_unit_title ?? "Target Unit",
    section_title: overrides.section_title ?? "Lecture 2",
    action: overrides.action ?? "standard_learn",
    estimated_hours: overrides.estimated_hours ?? 0.2,
    order_index: overrides.order_index ?? 0,
    week_number: overrides.week_number ?? 1,
    status: overrides.status ?? "pending",
    canonical_unit_id: overrides.canonical_unit_id ?? null,
    course_slug: overrides.course_slug,
    unit_slug: overrides.unit_slug,
    learn_href: overrides.learn_href,
  };
}

describe("LearningUnitDrawer mobile", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", vi.fn().mockImplementation((query: string) => ({
      matches: query === "(max-width: 767px)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })));

    useLearningPathStore.setState({
      items: [pathItem()],
      selectedItemId: "path-item-1",
      selectedSectionKey: null,
      updatingStatusById: {},
    });
  });

  it("renders selected lesson details inside the shared mobile sheet shell", () => {
    render(<LearningUnitDrawer />);

    expect(screen.getByRole("dialog", { name: "Target Unit" })).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Target Unit" }).className).toContain("mobile-sheet-panel");
  });
});
