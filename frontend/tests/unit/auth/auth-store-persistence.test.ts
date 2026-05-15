import { describe, expect, it, vi } from "vitest";

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

describe("useAuthStore persistence", () => {
  it("does not restore stale persisted auth errors", async () => {
    localStorage.setItem(
      "al-auth",
      JSON.stringify({
        state: {
          user: null,
          error: "An account with this email already exists.",
        },
        version: 0,
      }),
    );
    vi.resetModules();

    const { useAuthStore } = await import("@/stores/authStore");

    expect(useAuthStore.getState().error).toBeNull();
  });
});
