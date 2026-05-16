import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminLayout from "@/app/admin/layout";

const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
}));

const authStoreMock = vi.hoisted(() => ({
  user: null as { id: string; email: string; role: string } | null,
  fetchMe: vi.fn(),
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
  const useAuthStore = () => ({
    user: authStoreMock.user,
    fetchMe: authStoreMock.fetchMe,
  });
  useAuthStore.getState = () => ({
    user: authStoreMock.user,
  });
  return { useAuthStore };
});

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    tokenStorage: tokenStorageMock,
  };
});

vi.mock("@/components/admin/AdminSidebar", () => ({
  default: () => <aside>AdminSidebar</aside>,
}));

vi.mock("@/components/admin/AdminTopbar", () => ({
  default: () => <header>AdminTopbar</header>,
}));

describe("AdminLayout redirects", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authStoreMock.user = null;
    authStoreMock.fetchMe.mockResolvedValue(undefined);
    tokenStorageMock.getAccess.mockReturnValue("token");
  });

  it("returns missing-token users to the landing page", async () => {
    tokenStorageMock.getAccess.mockReturnValue("");

    render(
      <AdminLayout>
        <div>Admin content</div>
      </AdminLayout>,
    );

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith("/");
    });
  });

  it("routes non-admin authenticated users to the assistant", async () => {
    authStoreMock.user = {
      id: "user_1",
      email: "learner@example.com",
      role: "learner",
    };

    render(
      <AdminLayout>
        <div>Admin content</div>
      </AdminLayout>,
    );

    await waitFor(() => {
      expect(navigationMock.replace).toHaveBeenCalledWith("/agent");
    });
  });
});
