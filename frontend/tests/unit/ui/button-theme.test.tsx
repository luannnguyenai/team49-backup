import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Button from "@/components/ui/Button";

describe("Button theme contract", () => {
  it("keeps the primary button on the semantic button class", () => {
    render(<Button>Continue</Button>);

    const button = screen.getByRole("button", { name: "Continue" });
    expect(button.className).toContain("btn-primary");
  });

  it("keeps primary and secondary variants mapped to shared utility classes", () => {
    render(
      <>
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
      </>,
    );

    expect(screen.getByRole("button", { name: "Primary" }).className).toContain("btn-primary");
    expect(screen.getByRole("button", { name: "Secondary" }).className).toContain("btn-secondary");
  });
});
