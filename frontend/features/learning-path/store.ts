import { create } from "zustand";
import { learningPathApi } from "./api";
import type { LearningPathResponse, PathItemResponse, PathStatus, TimelineResponse } from "@/types";

interface LearningPathState {
  items: PathItemResponse[];
  summary: Omit<LearningPathResponse, "items"> | null;
  timeline: TimelineResponse | null;
  loading: boolean;
  error: string | null;
  selectedItemId: string | null;
  selectedSectionKey: string | null;
  updatingStatusById: Record<string, boolean>;
  loadPath: () => Promise<void>;
  selectItem: (id: string) => void;
  selectSection: (sectionKey: string) => void;
  closeDrawer: () => void;
  updateStatus: (pathId: string, status: PathStatus) => Promise<void>;
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Không tải được lộ trình. Vui lòng thử lại.";
}

function recomputeSummary(items: PathItemResponse[]): Omit<LearningPathResponse, "items"> {
  return {
    total_units: items.length,
    completed_units: items.filter((item) => item.status === "completed").length,
    in_progress_units: items.filter((item) => item.status === "in_progress").length,
  };
}

export const useLearningPathStore = create<LearningPathState>((set, get) => ({
  items: [],
  summary: null,
  timeline: null,
  loading: false,
  error: null,
  selectedItemId: null,
  selectedSectionKey: null,
  updatingStatusById: {},

  loadPath: async () => {
    set({ loading: true, error: null });
    try {
      const [path, timeline] = await Promise.all([
        learningPathApi.getLearningPath(),
        learningPathApi.getTimeline().catch(() => null),
      ]);
      set({
        items: path.items,
        summary: {
          total_units: path.total_units,
          completed_units: path.completed_units,
          in_progress_units: path.in_progress_units,
        },
        timeline,
        loading: false,
        error: null,
      });
    } catch (error) {
      set({ loading: false, error: toErrorMessage(error) });
    }
  },

  selectItem: (id) => set({ selectedItemId: id, selectedSectionKey: null }),
  selectSection: (sectionKey) => set({ selectedSectionKey: sectionKey, selectedItemId: null }),
  closeDrawer: () => set({ selectedItemId: null, selectedSectionKey: null }),

  updateStatus: async (pathId, status) => {
    const previousItems = get().items;
    const nextItems = previousItems.map((item) =>
      item.id === pathId ? { ...item, status } : item,
    );
    set((state) => ({
      items: nextItems,
      summary: recomputeSummary(nextItems),
      updatingStatusById: { ...state.updatingStatusById, [pathId]: true },
      error: null,
    }));

    try {
      await learningPathApi.updatePathStatus(pathId, status);
      set((state) => ({
        updatingStatusById: { ...state.updatingStatusById, [pathId]: false },
      }));
    } catch (error) {
      set((state) => ({
        items: previousItems,
        summary: recomputeSummary(previousItems),
        updatingStatusById: { ...state.updatingStatusById, [pathId]: false },
        error: toErrorMessage(error),
      }));
    }
  },
}));
