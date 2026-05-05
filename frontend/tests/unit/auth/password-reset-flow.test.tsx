import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";
import LoginForm from "@/components/auth/LoginForm";
import ResetPasswordForm from "@/components/auth/ResetPasswordForm";
import { authApi } from "@/lib/api";

const routerPushMock = vi.fn();
const loginMock = vi.fn();
const clearErrorMock = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => ({
      push: routerPushMock,
    }),
    useSearchParams: () => currentSearchParams,
  };
});

vi.mock("@/stores/authStore", () => ({
  useAuthStore: () => ({
    login: loginMock,
    isLoading: false,
    error: null,
    clearError: clearErrorMock,
  }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      requestPasswordReset: vi.fn(),
      confirmPasswordReset: vi.fn(),
    },
  };
});

describe("password reset flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentSearchParams = new URLSearchParams();
  });

  it("forgot password submits only email and shows a generic success message", async () => {
    vi.mocked(authApi.requestPasswordReset).mockResolvedValue({ status: "ok" });

    render(<ForgotPasswordForm />);

    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "learner@example.com" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Send reset link" }).closest("form")!);

    await waitFor(() => {
      expect(authApi.requestPasswordReset).toHaveBeenCalledWith({
        email: "learner@example.com",
      });
      expect(screen.getByText("If an account exists, we sent a reset link.")).toBeInTheDocument();
    });
  });

  it("reset password shows invalid state when token is missing", () => {
    render(<ResetPasswordForm />);

    expect(screen.getByText("This reset link is invalid.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Request a new reset link" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });

  it("reset password validates password confirmation", async () => {
    currentSearchParams = new URLSearchParams("token=reset-token-123");

    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass456!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "OtherPass456!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Reset password" }).closest("form")!);

    expect(await screen.findByText("Password confirmation does not match")).toBeInTheDocument();
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("reset password submits token and new password", async () => {
    currentSearchParams = new URLSearchParams("token=reset-token-123");
    vi.mocked(authApi.confirmPasswordReset).mockResolvedValue({ status: "ok" });

    render(<ResetPasswordForm />);

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass456!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "NewPass456!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Reset password" }).closest("form")!);

    await waitFor(() => {
      expect(authApi.confirmPasswordReset).toHaveBeenCalledWith({
        token: "reset-token-123",
        new_password: "NewPass456!",
      });
      expect(routerPushMock).toHaveBeenCalledWith("/login?reset=success");
    });
  });

  it("login shows password reset success banner", () => {
    currentSearchParams = new URLSearchParams("reset=success");

    render(<LoginForm />);

    expect(screen.getByText("Password reset successfully. Please sign in again.")).toBeInTheDocument();
  });
});
