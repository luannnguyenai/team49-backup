import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CourseCatalog from "@/components/course/CourseCatalog";
import { CS231N_ITEM } from "@/tests/fixtures/coursePlatform";

describe("CourseCatalog presentational hygiene", () => {
  it("renders the default empty message when no items are provided", () => {
    render(<CourseCatalog items={[]} />);

    expect(
      screen.getByText("Chưa có khóa học nào trong mục này."),
    ).toBeInTheDocument();
  });

  it("renders a custom emptyMessage from the parent when provided", () => {
    render(
      <CourseCatalog
        items={[]}
        emptyMessage="Không tìm thấy khóa học phù hợp với từ khóa của bạn."
      />,
    );

    expect(
      screen.getByText("Không tìm thấy khóa học phù hợp với từ khóa của bạn."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Chưa có khóa học nào trong mục này."),
    ).not.toBeInTheDocument();
  });

  it("renders course items and ignores emptyMessage when items exist", () => {
    render(
      <CourseCatalog
        items={[CS231N_ITEM]}
        emptyMessage="should-not-appear"
      />,
    );

    expect(screen.getByText(CS231N_ITEM.title)).toBeInTheDocument();
    expect(screen.queryByText("should-not-appear")).not.toBeInTheDocument();
  });
});
