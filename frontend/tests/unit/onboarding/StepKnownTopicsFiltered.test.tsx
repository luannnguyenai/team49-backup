import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import { useOnboardingStore } from "@/stores/onboardingStore";

const mockSectionList = [
  { id: "s1", title: "Convolutional Nets", canonical_course_id: "cs231n" },
  { id: "s2", title: "Transformers", canonical_course_id: "cs224n" },
];

const mockSectionDetails = {
  s1: {
    id: "s1",
    title: "Convolutional Nets",
    canonical_course_id: "cs231n",
    learning_units: [
      { id: "u1", title: "Conv Basics", estimated_hours_beginner: 1 },
    ],
  },
  s2: {
    id: "s2",
    title: "Transformers",
    canonical_course_id: "cs224n",
    learning_units: [
      { id: "u2", title: "Attention", estimated_hours_beginner: 2 },
    ],
  },
};

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
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => expect(screen.getByText("Convolutional Nets")).toBeInTheDocument());
    expect(screen.getByText("Conv Basics")).toBeInTheDocument();
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
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
    expect(onBackMock).toHaveBeenCalledOnce();
  });

  it("toggling a unit updates the store", async () => {
    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Conv Basics"));

    fireEvent.click(screen.getByText("Conv Basics"));
    expect(useOnboardingStore.getState().knownUnitIds).toContain("u1");

    fireEvent.click(screen.getByText("Conv Basics"));
    expect(useOnboardingStore.getState().knownUnitIds).not.toContain("u1");
  });

  it("filters to only cs231n sections when goalIds contains computer_vision", async () => {
    useOnboardingStore.getState().setGoalIds(["computer_vision"]);

    render(<StepKnownTopicsFiltered onNext={onNextMock} onBack={onBackMock} />);
    await waitFor(() => screen.getByText("Convolutional Nets"));

    expect(screen.getByText("Convolutional Nets")).toBeInTheDocument();
    expect(screen.queryByText("Transformers")).not.toBeInTheDocument();
  });
});
