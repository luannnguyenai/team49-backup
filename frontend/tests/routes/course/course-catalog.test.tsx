import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import CourseCatalog from "@/components/course/CourseCatalog";
import { CS231N_ITEM } from "@/tests/fixtures/coursePlatform";

describe("CourseCatalog presentational hygiene", () => {
  it("renders the default empty message when no items are provided", () => {
    render(<CourseCatalog items={[]} />);

    expect(
      screen.getByText("There are no courses in this section yet."),
    ).toBeInTheDocument();
  });

  it("renders a custom emptyMessage from the parent when provided", () => {
    render(
      <CourseCatalog
        items={[]}
        emptyMessage="No courses matched your keyword."
      />,
    );

    expect(
      screen.getByText("No courses matched your keyword."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("There are no courses in this section yet."),
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
