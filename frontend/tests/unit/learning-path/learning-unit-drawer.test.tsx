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

function resetStore(item: PathItemResponse) {
  useLearningPathStore.setState({
    items: [item],
    selectedItemId: item.id,
    selectedSectionKey: null,
    updatingStatusById: {},
  });
}

describe("LearningUnitDrawer", () => {
  beforeEach(() => {
    useLearningPathStore.setState({
      items: [],
      selectedItemId: null,
      selectedSectionKey: null,
      updatingStatusById: {},
    });
  });

  it("links the primary CTA to the canonical course player when available", () => {
    resetStore(
      pathItem({
        learn_href: "/courses/cs230/learn/lecture-02-seg3",
      }),
    );

    render(<LearningUnitDrawer />);

    expect(screen.getByRole("link", { name: "Start learning" })).toHaveAttribute(
      "href",
      "/courses/cs230/learn/lecture-02-seg3",
    );
  });

  it("falls back to the legacy learning-unit route when player slugs are missing", () => {
    resetStore(pathItem({ learning_unit_id: "legacy-unit-id" }));

    render(<LearningUnitDrawer />);

    expect(screen.getByRole("link", { name: "Start learning" })).toHaveAttribute(
      "href",
      "/learn/legacy-unit-id",
    );
  });
});
