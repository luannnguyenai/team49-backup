import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Sidebar from "@/components/layout/Sidebar";

const navigationMock = vi.hoisted(() => ({
  pathname: "/dashboard",
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  },
}));

const authStoreMock = vi.hoisted(() => ({
  user: {
    id: "user_1",
    full_name: "Test User",
    email: "test@example.com",
  },
  logout: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    usePathname: () => navigationMock.pathname,
    useRouter: () => navigationMock.router,
  };
});

vi.mock("@/stores/authStore", () => ({
  useAuthStore: () => ({
    user: authStoreMock.user,
    logout: authStoreMock.logout,
  }),
}));

describe("Sidebar logout routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationMock.pathname = "/dashboard";
  });

  it("returns the user to the landing page after logout", async () => {
    let resolveLogout!: () => void;
    authStoreMock.logout.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveLogout = resolve;
        }),
    );

    render(<Sidebar mobileOpen={false} onMobileClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(authStoreMock.logout).toHaveBeenCalledTimes(1);
    expect(navigationMock.router.push).not.toHaveBeenCalled();

    resolveLogout();

    await waitFor(() => {
      expect(navigationMock.router.push).toHaveBeenCalledWith("/");
    });
  });

  it("does not render the public Courses root link in the protected sidebar", () => {
    render(<Sidebar mobileOpen={false} onMobileClose={vi.fn()} />);

    expect(screen.queryByRole("link", { name: "Courses" })).not.toBeInTheDocument();
  });
});
