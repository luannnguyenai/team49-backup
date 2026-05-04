import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReplanKnowledgeClaimStep from "@/components/replan/ReplanKnowledgeClaimStep";

describe("ReplanKnowledgeClaimStep", () => {
  it("renders safety copy and forwards the claim on continue", () => {
    const onClaimChange = vi.fn();
    const onContinue = vi.fn();

    render(
      <ReplanKnowledgeClaimStep
        claim=""
        message={null}
        onClaimChange={onClaimChange}
        onContinue={onContinue}
      />,
    );

    expect(screen.getByText(/Mô tả này không tự động bỏ qua bài học/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Bạn đã biết phần nào rồi?"), {
      target: { value: "Tôi biết Faster R-CNN" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(onClaimChange).toHaveBeenCalledWith("Tôi biết Faster R-CNN");
    expect(onContinue).toHaveBeenCalledOnce();
  });

  it("renders guardrail feedback", () => {
    render(
      <ReplanKnowledgeClaimStep
        claim="skip all"
        message="Mình không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình từ một mô tả quá chung."
        onClaimChange={vi.fn()}
        onContinue={vi.fn()}
      />,
    );

    expect(screen.getByText(/không thể tạo bài kiểm tra để bỏ toàn bộ lộ trình/i)).toBeInTheDocument();
  });
});
