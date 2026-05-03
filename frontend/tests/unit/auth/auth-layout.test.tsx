import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AuthLayout from "@/app/(auth)/layout";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("AuthLayout", () => {
  it("does not render the back-to-landing link inside the shared auth layout", () => {
    render(
      <AuthLayout>
        <div>Auth content</div>
      </AuthLayout>,
    );

    expect(screen.queryByRole("link", { name: "Back to Landing Page" })).not.toBeInTheDocument();
  });
});
