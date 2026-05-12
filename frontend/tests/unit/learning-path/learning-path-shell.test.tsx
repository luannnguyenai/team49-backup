import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LearningPathShell from "@/features/learning-path/components/LearningPathShell";
import { createLearningProfileForPath } from "@/features/learning-path/profile";
import { useLearningPathStore } from "@/features/learning-path/store";

const navigationMock = {
  pathname: "/learn",
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
};

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    usePathname: () => navigationMock.pathname,
    useRouter: () => ({ replace: navigationMock.replace }),
    useSearchParams: () => navigationMock.searchParams,
  };
});

vi.mock("@/features/learning-path/components/PlannerHeader", () => ({
  default: () => <div>Planner header mock</div>,
}));

vi.mock("@/features/learning-path/components/ProfileChangeBanner", () => ({
  default: () => null,
}));

vi.mock("@/features/learning-path/components/TimelineBoard", () => ({
  default: () => <div>Timeline board mock</div>,
}));

vi.mock("@/features/learning-path/components/LearningUnitDrawer", () => ({
  default: () => null,
}));

vi.mock("@/features/learning-path/components/RoadmapCanvas", () => ({
  default: () => <div>Graph canvas mock</div>,
}));

describe("LearningPathShell mobile view handling", () => {
  beforeEach(() => {
    navigationMock.pathname = "/learn";
    navigationMock.replace.mockReset();
    navigationMock.searchParams = new URLSearchParams();
    localStorage.clear();

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
      profile: createLearningProfileForPath("computer_vision", {
        weeklyHours: 5,
        source: "manual",
      }),
      previousProfile: null,
      generatedTopologyHash: null,
      items: [
        {
          id: "path-item-1",
          learning_unit_id: "unit-1",
          learning_unit_title: "Target Unit",
          section_title: "Lecture 2",
          action: "standard_learn",
          estimated_hours: 0.2,
          order_index: 0,
          week_number: 1,
          status: "pending",
          canonical_unit_id: null,
        },
      ],
      summary: { total_units: 1, completed_units: 0, in_progress_units: 0 },
      loading: false,
      error: null,
      loadPath: vi.fn(async () => {}),
      setProfile: vi.fn(),
    });
  });

  it("defaults mobile users into the weekly timeline when no view is requested", () => {
    render(<LearningPathShell />);

    expect(screen.getByText("Timeline board mock")).toBeInTheDocument();
    expect(screen.queryByText("Graph canvas mock")).not.toBeInTheDocument();
  });

  it("replaces graph mode with a mobile-safe weekly fallback and lets the user switch back", () => {
    navigationMock.searchParams = new URLSearchParams("view=graph");

    render(<LearningPathShell />);

    expect(screen.getByText("Graph view works best on a larger screen.")).toBeInTheDocument();
    expect(screen.getByText("Timeline board mock")).toBeInTheDocument();
    expect(screen.queryByText("Graph canvas mock")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Switch to weekly view" }));

    expect(navigationMock.replace).toHaveBeenCalledWith("/learn?view=timeline", { scroll: false });
  });
});
