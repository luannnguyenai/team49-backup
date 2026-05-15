import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginForm from "@/components/auth/LoginForm";
import RegisterForm from "@/components/auth/RegisterForm";
import { useAuthStore } from "@/stores/authStore";

vi.mock("@/lib/api", () => ({
  authApi: {
    logout: vi.fn(),
    register: vi.fn(),
    login: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    onboarding: vi.fn(),
  },
  tokenStorage: {
    clear: vi.fn(),
    getExpiresAt: vi.fn(() => 0),
    getRefresh: vi.fn(() => null),
    set: vi.fn(),
  },
}));

describe("auth form error lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.setState({
      user: null,
      isLoading: false,
      error: null,
      _refreshTimer: null,
    });
  });

  it("clears stale register errors when the register form is opened again", async () => {
    useAuthStore.setState({ error: "An account with this email already exists." });

    render(<RegisterForm />);

    await waitFor(() => {
      expect(screen.queryByText("An account with this email already exists.")).not.toBeInTheDocument();
    });
    expect(useAuthStore.getState().error).toBeNull();
  });

  it("clears stale login errors when the login form is opened again", async () => {
    useAuthStore.setState({ error: "Invalid email or password." });

    render(<LoginForm />);

    await waitFor(() => {
      expect(screen.queryByText("Invalid email or password.")).not.toBeInTheDocument();
    });
    expect(useAuthStore.getState().error).toBeNull();
  });
});
