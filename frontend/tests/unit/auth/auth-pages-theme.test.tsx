import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/(auth)/login/page";
import RegisterPage from "@/app/(auth)/register/page";
import ForgotPasswordPage from "@/app/(auth)/forgot-password/page";

describe("Auth pages theme contract", () => {
  it.each([
    ["login", LoginPage, /welcome back/i],
    ["register", RegisterPage, /create your account/i],
    ["forgot-password", ForgotPasswordPage, /reset your password/i],
  ])("%s page title uses semantic text classes", (_name, Page, heading) => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: heading }).className).toContain("text-text-strong");
  });
});
