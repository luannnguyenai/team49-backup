import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginForm from "@/components/auth/LoginForm";
import RegisterForm from "@/components/auth/RegisterForm";

const routerPushMock = vi.fn();
const loginMock = vi.fn();
const registerUserMock = vi.fn();
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
    register: registerUserMock,
    isLoading: false,
    error: null,
    clearError: clearErrorMock,
  }),
}));

describe("auth forms preserve next redirect context", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentSearchParams = new URLSearchParams("next=/courses/cs231n/start");
  });

  it("login form submits back to the preserved next target", async () => {
    loginMock.mockResolvedValue(undefined);

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "learner@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), {
      target: { value: "password1" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Đăng nhập" }).closest("form")!);

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "learner@example.com",
        password: "password1",
      });
      expect(routerPushMock).toHaveBeenCalledWith("/courses/cs231n/start");
    });
  });

  it("login form preserves next on the register link", () => {
    render(<LoginForm />);

    expect(screen.getByRole("link", { name: "Đăng ký ngay" })).toHaveAttribute(
      "href",
      "/register?next=%2Fcourses%2Fcs231n%2Fstart",
    );
  });

  it("login form preserves next on the forgot-password link", () => {
    render(<LoginForm />);

    expect(screen.getByRole("link", { name: "Quên mật khẩu?" })).toHaveAttribute(
      "href",
      "/forgot-password?next=%2Fcourses%2Fcs231n%2Fstart",
    );
  });

  it("register form submits onboarding with preserved next", async () => {
    registerUserMock.mockResolvedValue(undefined);

    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("Họ và tên"), {
      target: { value: "Learner Example" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "learner@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), {
      target: { value: "password1" },
    });
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu"), {
      target: { value: "password1" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Tạo tài khoản" }).closest("form")!);

    await waitFor(() => {
      expect(registerUserMock).toHaveBeenCalledWith({
        email: "learner@example.com",
        password: "password1",
        full_name: "Learner Example",
      });
      expect(routerPushMock).toHaveBeenCalledWith(
        "/onboarding?next=%2Fcourses%2Fcs231n%2Fstart",
      );
    });
  });

  it("register form preserves next on the login link", () => {
    render(<RegisterForm />);

    expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute(
      "href",
      "/login?next=%2Fcourses%2Fcs231n%2Fstart",
    );
  });
});
