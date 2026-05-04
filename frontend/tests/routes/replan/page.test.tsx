import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ReplanPage from "@/app/replan/page";

describe("replan page", () => {
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
});
