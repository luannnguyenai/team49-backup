import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ProtectedLayout from "@/app/(protected)/layout";

const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
}));

const authStoreMock = vi.hoisted(() => ({
  user: null as { id: string; full_name: string; is_onboarded: boolean } | null,
  fetchMe: vi.fn(() => new Promise(() => {})),
}));

const tokenStorageMock = vi.hoisted(() => ({
  getAccess: vi.fn(() => "token"),
}));

vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => navigationMock,
  };
});

vi.mock("@/stores/authStore", () => {
  return {
    useAuthStore: () => ({
      user: authStoreMock.user,
      fetchMe: authStoreMock.fetchMe,
    }),
  };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    tokenStorage: tokenStorageMock,
  };
});

vi.mock("@/components/layout/TopNav", () => ({
  default: () => <div>TopNav</div>,
}));

describe("ProtectedLayout", () => {
  it("renders children immediately when an access token already exists", () => {
    render(
      <ProtectedLayout>
        <div>Protected content</div>
      </ProtectedLayout>,
    );

    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });
});
