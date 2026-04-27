import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
const { mockSectionList, mockSectionDetails } = vi.hoisted(() => {
  const mockSectionList = [
  { id: "s0", title: "Deep Learning Basics", canonical_course_id: "cs230" },
  { id: "s1", title: "Convolutional Nets", canonical_course_id: "cs231n" },
  { id: "s2", title: "Transformers", canonical_course_id: "cs224n" },
  ];

  const mockSectionDetails = {
  s0: {
    id: "s0",
    course_id: "c0",
    title: "Deep Learning Basics",
    description: null,
    order_index: 0,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    canonical_course_id: "cs230",
    learning_units: [
      {
        id: "u0",
        title: "Neural Networks",
        description: null,
        order_index: 0,
        estimated_hours_beginner: 1,
        estimated_hours_intermediate: 0.5,
      },
    ],
  },
  s1: {
    id: "s1",
    course_id: "c1",
    title: "Convolutional Nets",
    description: null,
    order_index: 1,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    canonical_course_id: "cs231n",
    learning_units: [
      {
        id: "u1",
        title: "Conv Basics",
        description: null,
        order_index: 0,
        estimated_hours_beginner: 1,
        estimated_hours_intermediate: 0.5,
      },
    ],
  },
  s2: {
    id: "s2",
    course_id: "c2",
    title: "Transformers",
    description: null,
    order_index: 2,
    prerequisite_section_ids: null,
    learning_units_count: 1,
    canonical_course_id: "cs224n",
    learning_units: [
      {
        id: "u2",
        title: "Attention",
        description: null,
        order_index: 0,
        estimated_hours_beginner: 2,
        estimated_hours_intermediate: 1,
      },
    ],
  },
  };

  return { mockSectionList, mockSectionDetails };
});

import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import { useOnboardingStore } from "@/stores/onboardingStore";

vi.mock("@/lib/api", () => ({
  canonicalSectionApi: {
    list: vi.fn().mockResolvedValue(mockSectionList),
    detail: vi.fn((id: string) => Promise.resolve(mockSectionDetails[id as keyof typeof mockSectionDetails])),
  },
}));

describe("StepKnownTopicsFiltered", () => {
  const onNextMock = vi.fn();
  const onBackMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useOnboardingStore.getState().reset();
  });

  it("shows loading state initially", () => {
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    expect(screen.getByText("Đang tải...")).toBeInTheDocument();
  });

  it("renders sections after data loads", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => expect(screen.getByText("Convolutional Nets")).toBeInTheDocument());
    expect(screen.getByText("Deep Learning Basics")).toBeInTheDocument();
  });

  it("shows error message when API fails", async () => {
    const { canonicalSectionApi } = await import("@/lib/api");
    vi.mocked(canonicalSectionApi.list).mockRejectedValueOnce(new Error("network error"));

    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() =>
      expect(screen.getByText("Không thể tải dữ liệu. Vui lòng thử lại.")).toBeInTheDocument(),
    );
  });

  it("calls onBack when Back button clicked", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
    expect(onBackMock).toHaveBeenCalledOnce();
  });

  it("rating a cluster selects representative units", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    fireEvent.click(screen.getAllByRole("button", { name: "Đã học qua" })[1]);
    expect(useOnboardingStore.getState().knownUnitIds).toContain("u1");

    fireEvent.click(screen.getAllByRole("button", { name: "Chưa học" })[1]);
    expect(useOnboardingStore.getState().knownUnitIds).not.toContain("u1");
  });

  it("filters to foundation and target sections when goalIds contains computer_vision", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);

    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    expect(screen.getByText("Deep Learning Basics")).toBeInTheDocument();
    expect(screen.getByText("Convolutional Nets")).toBeInTheDocument();
    expect(screen.queryByText("Transformers")).not.toBeInTheDocument();
  });

  it("eye button reveals representative units without rendering raw checklist by default", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);

    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    expect(screen.queryByText("Conv Basics")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xem nhanh Convolutional Nets" }));
    expect(screen.getByText("- Conv Basics")).toBeInTheDocument();
  });
});
