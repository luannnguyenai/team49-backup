import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import KpiCard from "@/components/admin/KpiCard";

describe("KpiCard", () => {
  it("shows a two-layer tooltip on hover", async () => {
    const user = userEvent.setup();

    render(
      <KpiCard
        label="Error rate"
        value="1.25%"
        tooltip={{
          summary: "Ty le request backend bi loi phia server.",
          detail: "Tinh tu HTTP 5xx / tong request trong 5 phut gan nhat tu Prometheus.",
        }}
      />,
    );

    expect(
      screen.queryByText("Ty le request backend bi loi phia server."),
    ).not.toBeInTheDocument();

    await user.hover(screen.getByLabelText("More info for Error rate"));

    expect(
      screen.getByText("Ty le request backend bi loi phia server."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Tinh tu HTTP 5xx / tong request trong 5 phut gan nhat tu Prometheus."),
    ).toBeInTheDocument();
  });
});
