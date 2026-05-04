import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReplanPage from "@/app/replan/page";
import { readPendingCanonicalAssessment } from "@/lib/canonical-assessment-session";

const navigationMock = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

describe("replan page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
  });

  it("renders a scope-builder wizard without a cancel flow", () => {
    render(<ReplanPage />);

    expect(screen.getByRole("heading", { name: "Tối ưu lộ trình học" })).toBeInTheDocument();
    expect(screen.getByText(/Mô tả này không tự động bỏ qua bài học/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Bạn đã biết phần nào rồi?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
  });

  it("shows guardrail feedback before continuing", () => {
    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "skip all" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(/không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình/i)).toBeInTheDocument();
  });

  it("continues from a valid claim to scope review and starts the existing assessment flow", () => {
    render(<ReplanPage />);

    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "I know Faster R-CNN and CNN feature extraction" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText("Review verification scope")).toBeInTheDocument();
    expect(screen.getByText("Faster R-CNN")).toBeInTheDocument();
    expect(screen.getByText("Region Proposal Network")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));

    expect(readPendingCanonicalAssessment()).toMatchObject({
      canonicalUnitIds: ["unit_faster_rcnn"],
      unitNameMap: {
        unit_faster_rcnn: "Faster R-CNN",
      },
      assessmentDepth: "deep",
    });
    expect(navigationMock.push).toHaveBeenCalledWith("/assessment?next=%2Flearn");
  });
});
