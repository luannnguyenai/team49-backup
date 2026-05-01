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
  it("renders a back-to-landing link in the auth card header", () => {
    render(
      <AuthLayout>
        <div>Auth content</div>
      </AuthLayout>,
    );

    expect(screen.getByRole("link", { name: "Back to Landing Page" })).toHaveAttribute("href", "/");
  });
});
