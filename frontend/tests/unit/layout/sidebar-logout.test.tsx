import { fireEvent, render, screen } from "@testing-library/react";
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

  it("returns the user to the landing page after logout", () => {
    render(<Sidebar mobileOpen={false} onMobileClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));

    expect(authStoreMock.logout).toHaveBeenCalledTimes(1);
    expect(navigationMock.router.push).toHaveBeenCalledWith("/");
  });
});
