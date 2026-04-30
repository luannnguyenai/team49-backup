import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/(auth)/login/page";
import RegisterPage from "@/app/(auth)/register/page";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/auth/LoginForm", () => ({
  default: () => <div data-testid="login-form">Login form</div>,
}));

vi.mock("@/components/auth/RegisterForm", () => ({
  default: () => <div data-testid="register-form">Register form</div>,
}));

describe("auth pages", () => {
  it("renders the back-to-landing link below the login form", () => {
    render(<LoginPage />);

    const form = screen.getByTestId("login-form");
    const link = screen.getByRole("link", { name: "Back to Landing Page" });

    expect(link).toHaveAttribute("href", "/");
    expect(form.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders the back-to-landing link below the register form", () => {
    render(<RegisterPage />);

    const form = screen.getByTestId("register-form");
    const link = screen.getByRole("link", { name: "Back to Landing Page" });

    expect(link).toHaveAttribute("href", "/");
    expect(form.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
