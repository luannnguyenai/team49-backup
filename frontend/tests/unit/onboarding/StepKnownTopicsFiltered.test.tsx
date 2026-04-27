import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import StepKnownTopicsFiltered from "@/components/onboarding/StepKnownTopicsFiltered";
import {
  buildPriorCandidateTopics,
  buildPriorShortlistFallback,
  displayLabelForSectionTitle,
  selectSuggestedKnownUnitIds,
} from "@/components/onboarding/priorCandidateBuilder";
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
}).confirmEligible.map((topic) => ({
  ...topic,
  summary: "Tóm tắt CNN, kiến trúc mạng tích chập và các bài toán thị giác phổ biến.",
}));

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

  it("uses rewritten topic labels from AI when available", () => {
    render(
      <StepKnownTopicsFiltered
        topics={[
          {
            ...cvTopics[0],
            aiDisplayLabel: "Vision CNN fundamentals",
          },
        ]}
        modelLabel="openai/gpt-5.4-mini"
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    expect(screen.getByText("Vision CNN fundamentals")).toBeInTheDocument();
    expect(screen.queryByText("CNN architectures")).not.toBeInTheDocument();
  });

  it("preselects representative units from AI-suggested confidence levels", () => {
    const suggested = selectSuggestedKnownUnitIds([
      {
        ...cvTopics[0],
        suggestedLevel: "confident",
      },
    ]);

    expect(suggested).toContain("u1");
  });

  it("rewrites unclear lecture titles into learner-friendly labels", () => {
    expect(displayLabelForSectionTitle("Lecture 9: What Is Going On Inside My Model?")).toBe(
      "Model interpretability",
    );
  });

  it("does not fallback to a fixed top shortlist when user text has no concrete match", () => {
    const topics = buildPriorCandidateTopics({
      goalId: "computer_vision",
      sections,
    }).confirmEligible;

    const fallback = buildPriorShortlistFallback({
      topics,
      priorKnowledgeText: "",
      codingExperienceText: "",
    });

    expect(fallback).toEqual([]);
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

  it("does not render assessment depth in topic confirmation", () => {
    render(
      <StepKnownTopicsFiltered
        topics={cvTopics}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

    expect(screen.queryByText("Mức kiểm tra")).not.toBeInTheDocument();
    expect(screen.queryByText("Nhanh")).not.toBeInTheDocument();
  });

  it("eye button reveals a summarized representative content preview", () => {
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
    expect(
      screen.getByText("Tóm tắt CNN, kiến trúc mạng tích chập và các bài toán thị giác phổ biến."),
    ).toBeInTheDocument();
    expect(screen.queryByText("- Conv Basics")).not.toBeInTheDocument();
  });

  it("falls back to raw representative units when no AI summary exists", () => {
    const topicsWithoutSummary = cvTopics.map(({ summary: _summary, ...topic }) => topic);

    render(
      <StepKnownTopicsFiltered
        topics={topicsWithoutSummary}
        onNext={onNextMock}
        onBack={onBackMock}
        onSkipAll={onSkipAllMock}
      />,
    );

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
