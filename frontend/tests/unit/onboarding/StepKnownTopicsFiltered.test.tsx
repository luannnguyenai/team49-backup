import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import { buildPriorCandidateTopics } from "@/components/onboarding/priorCandidateBuilder";
import { useOnboardingStore } from "@/stores/onboardingStore";
import type { CourseSectionDetail } from "@/types";

const sections = [
  {
    id: "s1",
    course_id: "c1",
    title: "Lecture 6: CNN Architectures",
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
  {
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
] satisfies CourseSectionDetail[];

const cvTopics = buildPriorCandidateTopics({
  goalId: "computer_vision",
  sections,
}).confirmEligible;

describe("StepKnownTopicsFiltered", () => {
  const onNextMock = vi.fn();
  const onBackMock = vi.fn();
  const onSkipAllMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useOnboardingStore.getState().reset();
  });

  it("renders only the AI-selected confirmation shortlist", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        modelLabel="openai/gpt-5.4-mini"
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    expect(screen.getByText("CNN architectures")).toBeInTheDocument();
    expect(screen.queryByText("Transformers")).not.toBeInTheDocument();
    expect(screen.getByText("Shortlist được tạo bởi openai/gpt-5.4-mini.")).toBeInTheDocument();
  });

  it("lets the user select representative units", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Đã học qua CNN architectures" }));
    expect(useOnboardingStore.getState().knownUnitIds).toContain("u1");

    fireEvent.click(screen.getByRole("button", { name: "Chưa học CNN architectures" }));
    expect(useOnboardingStore.getState().knownUnitIds).not.toContain("u1");
  });

  it("lets the user choose assessment depth", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    expect(screen.getByText("Nhanh")).toBeInTheDocument();
    expect(screen.getByText("tối đa 15 câu")).toBeInTheDocument();
    expect(screen.getByText("easy/medium")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Kỹ/i }));
    expect(useOnboardingStore.getState().assessmentDepth).toBe("deep");
  });

  it("eye button reveals representative units without showing them by default", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    expect(screen.queryByText("Conv Basics")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xem nhanh CNN architectures" }));
    expect(screen.getByText("- Conv Basics")).toBeInTheDocument();
  });

  it("calls navigation handlers", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
    fireEvent.click(screen.getByRole("button", { name: "Bỏ qua" }));
    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));

    expect(onBackMock).toHaveBeenCalledOnce();
    expect(onSkipAllMock).toHaveBeenCalledOnce();
    expect(onNextMock).toHaveBeenCalledOnce();
  });
});
