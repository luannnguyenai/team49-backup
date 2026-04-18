// stores/authStore.ts
// Zustand auth store with auto token-refresh scheduling

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { authApi, tokenStorage } from "@/lib/api";
import type {
  LoginPayload,
  OnboardingPayload,
  RegisterPayload,
  User,
} from "@/types";
import { getErrorMessage } from "@/lib/utils";

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  _refreshTimer: ReturnType<typeof setTimeout> | null;

  // Actions
  register: (payload: RegisterPayload) => Promise<void>;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  fetchMe: () => Promise<void>;
  onboard: (payload: OnboardingPayload) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Helper: schedule silent token refresh 60 s before expiry
// ---------------------------------------------------------------------------

function scheduleRefresh(
  get: () => AuthState,
  set: (partial: Partial<AuthState>) => void
) {
  const existing = get()._refreshTimer;
  if (existing) clearTimeout(existing);

  const expiresAt = tokenStorage.getExpiresAt();
  if (!expiresAt) return;

  const delay = Math.max(expiresAt - Date.now() - 60_000, 0);

  const timer = setTimeout(async () => {
    const ok = await get().refreshToken();
    if (ok) scheduleRefresh(get, set);
  }, delay);

  set({ _refreshTimer: timer });
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      error: null,
      _refreshTimer: null,

      clearError: () => set({ error: null }),

      // ---- register ----
      register: async (payload) => {
        set({ isLoading: true, error: null });
        try {
          const tokens = await authApi.register(payload);
          tokenStorage.set(
            tokens.access_token,
            tokens.refresh_token,
            tokens.expires_in
          );
          const user = await authApi.me();
          set({ user, isLoading: false });
          scheduleRefresh(get, set);
        } catch (err: unknown) {
          const msg = getErrorMessage(
            (err as { response?: { data: unknown } })?.response?.data ?? err
          );
          set({ isLoading: false, error: msg });
          throw err;
        }
      },

      // ---- login ----
      login: async (payload) => {
        set({ isLoading: true, error: null });
        try {
          const tokens = await authApi.login(payload);
          tokenStorage.set(
            tokens.access_token,
            tokens.refresh_token,
            tokens.expires_in
          );
          const user = await authApi.me();
          set({ user, isLoading: false });
          scheduleRefresh(get, set);
        } catch (err: unknown) {
          const msg = getErrorMessage(
            (err as { response?: { data: unknown } })?.response?.data ?? err
          );
          set({ isLoading: false, error: msg });
          throw err;
        }
      },

      // ---- logout ----
      logout: async () => {
        const timer = get()._refreshTimer;
        if (timer) clearTimeout(timer);
        try {
          await authApi.logout();
        } catch {
          // Best-effort revoke; local cleanup must still happen.
        } finally {
          tokenStorage.clear();
          set({ user: null, error: null, _refreshTimer: null });
        }
      },

      // ---- refresh ----
      refreshToken: async () => {
        const refreshToken = tokenStorage.getRefresh();
        if (!refreshToken) return false;
        try {
          const result = await authApi.refresh(refreshToken);
          const existingRefresh = tokenStorage.getRefresh()!;
          tokenStorage.set(
            result.access_token,
            existingRefresh,
            result.expires_in
          );
          return true;
        } catch {
          await get().logout();
          return false;
        }
      },

      // ---- fetch current user ----
      fetchMe: async () => {
        set({ isLoading: true, error: null });
        try {
          const user = await authApi.me();
          set({ user, isLoading: false });
        } catch {
          set({ isLoading: false });
        }
      },

      // ---- onboarding ----
      onboard: async (payload) => {
        set({ isLoading: true, error: null });
        try {
          const user = await authApi.onboarding(payload);
          set({ user, isLoading: false });
        } catch (err: unknown) {
          const msg = getErrorMessage(
            (err as { response?: { data: unknown } })?.response?.data ?? err
          );
          set({ isLoading: false, error: msg });
          throw err;
        }
      },
    }),
    {
      name: "al-auth",
      // Only persist the user object — tokens live in cookies
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user }),
    }
  )
);
