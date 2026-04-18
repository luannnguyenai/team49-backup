import { beforeEach, describe, expect, it, vi } from "vitest";

const logoutMock = vi.fn();
const clearMock = vi.fn();
const getExpiresAtMock = vi.fn(() => 0);
const getRefreshMock = vi.fn(() => null);
const setMock = vi.fn();

vi.mock("@/lib/api", () => ({
  authApi: {
    logout: logoutMock,
    register: vi.fn(),
    login: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    onboarding: vi.fn(),
  },
  tokenStorage: {
    clear: clearMock,
    getExpiresAt: getExpiresAtMock,
    getRefresh: getRefreshMock,
    set: setMock,
  },
}));

describe("useAuthStore.logout", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    localStorage.clear();
    const { useAuthStore } = await import("@/stores/authStore");
    useAuthStore.setState({
      user: {
        id: "user-1",
        email: "learner@example.com",
        full_name: "Learner Example",
        available_hours_per_week: null,
        target_deadline: null,
        preferred_method: null,
        is_onboarded: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: "stale error",
      _refreshTimer: setTimeout(() => {}, 60_000),
    });
  });

  it("calls backend logout and clears local auth state", async () => {
    logoutMock.mockResolvedValue(undefined);
    const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");

    const { useAuthStore } = await import("@/stores/authStore");
    await useAuthStore.getState().logout();

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(clearMock).toHaveBeenCalledTimes(1);
    expect(clearTimeoutSpy).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().error).toBeNull();
    expect(useAuthStore.getState()._refreshTimer).toBeNull();
  });

  it("still clears local auth state when backend logout fails", async () => {
    logoutMock.mockRejectedValue(new Error("network"));

    const { useAuthStore } = await import("@/stores/authStore");
    await useAuthStore.getState().logout();

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(clearMock).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().error).toBeNull();
    expect(useAuthStore.getState()._refreshTimer).toBeNull();
  });
});
