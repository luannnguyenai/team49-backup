// stores/courseCatalogStore.ts
// Zustand store for catalog view state management (recommended + all-courses tabs)

import { create } from "zustand";
import { courseApi } from "@/lib/api";
import type { CourseCatalogItem, CourseCatalogView } from "@/types";

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface CourseCatalogState {
  activeView: CourseCatalogView;
  allCourses: CourseCatalogItem[];
  recommendedCourses: CourseCatalogItem[];
  isLoading: boolean;
  error: string | null;
  hasRecommendations: boolean;

  // Actions
  setActiveView: (view: CourseCatalogView) => void;
  loadAllCourses: () => Promise<void>;
  loadRecommendedCourses: () => Promise<void>;
  loadCatalog: (opts?: { isAuthenticated?: boolean }) => Promise<void>;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useCourseCatalogStore = create<CourseCatalogState>()((set, get) => ({
  activeView: "all",
  allCourses: [],
  recommendedCourses: [],
  isLoading: false,
  error: null,
  hasRecommendations: false,

  setActiveView: (view) => set({ activeView: view }),

  loadAllCourses: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await courseApi.catalog({
        view: "all",
        includeUnavailable: true,
      });
      set({
        allCourses: response.items,
        isLoading: false,
      });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load course catalog.",
      });
    }
  },

  loadRecommendedCourses: async () => {
    try {
      const response = await courseApi.catalog({
        view: "recommended",
        includeUnavailable: true,
      });
      set({
        recommendedCourses: response.items,
        hasRecommendations: response.items.length > 0,
      });
    } catch {
      // Recommendation failures are non-fatal — user can still use all-courses
      set({ recommendedCourses: [], hasRecommendations: false });
    }
  },

  loadCatalog: async (opts) => {
    const { loadAllCourses, loadRecommendedCourses } = get();

    // Always load all courses
    await loadAllCourses();

    // Load recommendations only for authenticated users
    if (opts?.isAuthenticated) {
      await loadRecommendedCourses();
    }
  },

  reset: () =>
    set({
      activeView: "all",
      allCourses: [],
      recommendedCourses: [],
      isLoading: false,
      error: null,
      hasRecommendations: false,
    }),
}));
