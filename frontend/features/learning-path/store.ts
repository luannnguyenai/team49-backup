import { create } from "zustand";
import { persist } from "zustand/middleware";
import { learningSessionApi } from "@/lib/api";
import { learningPathApi } from "./api";
import type { LearningPathResponse, PathItemResponse, PathStatus, TimelineResponse } from "@/types";
import type { PlayerProgressSnapshot } from "./player-insights";
import type { LearningProfile } from "./profile";

interface LearningPathState {
  profile: LearningProfile | null;
  generatedTopologyHash: string | null;
  previousProfile: LearningProfile | null;
  currentProgress: PlayerProgressSnapshot | null;
  items: PathItemResponse[];
  summary: Omit<LearningPathResponse, "items"> | null;
  timeline: TimelineResponse | null;
  loading: boolean;
  error: string | null;
  selectedItemId: string | null;
  selectedSectionKey: string | null;
  updatingStatusById: Record<string, boolean>;
  setProfile: (profile: LearningProfile | null) => void;
  setCurrentProgress: (snapshot: PlayerProgressSnapshot | null) => void;
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

function toNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function toBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function toPlayerProgressSnapshot(
  learningUnitId: string | null | undefined,
  progress: Record<string, unknown> | null | undefined,
): PlayerProgressSnapshot | null {
  if (!learningUnitId || !progress) return null;
  return {
    learning_unit_id: learningUnitId,
    video_progress_s: toNumber(progress.video_progress_s),
    watch_percent: toNumber(progress.watch_percent),
    video_finished: toBoolean(progress.video_finished),
    inline_quiz: (progress.inline_quiz as PlayerProgressSnapshot["inline_quiz"]) ?? null,
    review_due_count: toNumber(progress.review_due_count),
    mastery_stale: toBoolean(progress.mastery_stale),
    has_end_quiz: toBoolean(progress.has_end_quiz),
  };
}

export const useLearningPathStore = create<LearningPathState>()(
  persist(
    (set, get) => ({
      profile: null,
      generatedTopologyHash: null,
      previousProfile: null,
      currentProgress: null,
      items: [],
      summary: null,
      timeline: null,
      loading: false,
      error: null,
      selectedItemId: null,
      selectedSectionKey: null,
      updatingStatusById: {},

      setProfile: (profile) =>
        set((state) => ({
          profile,
          previousProfile: state.profile,
          generatedTopologyHash: profile ? state.generatedTopologyHash : null,
        })),

      setCurrentProgress: (snapshot) => set({ currentProgress: snapshot }),

      loadPath: async () => {
        set({ loading: true, error: null });
        try {
          const [path, timeline, resume] = await Promise.all([
            learningPathApi.getLearningPath(),
            learningPathApi.getTimeline().catch(() => null),
            learningSessionApi.resume().catch(() => null),
          ]);
          set({
            items: path.items,
            summary: {
              total_units: path.total_units,
              completed_units: path.completed_units,
              in_progress_units: path.in_progress_units,
            },
            timeline,
            currentProgress: toPlayerProgressSnapshot(
              resume?.current_unit_id,
              resume?.current_progress,
            ),
            generatedTopologyHash: get().profile?.topologyHash ?? null,
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
    }),
    {
      name: "learn:path-profile",
      partialize: (state) => ({
        profile: state.profile,
        generatedTopologyHash: state.generatedTopologyHash,
      }),
    },
  ),
);
