import { api } from "@/lib/api";
import type {
  GeneratePathRequest,
  GeneratePathResponse,
  LearningPathResponse,
  PathStatus,
  TimelineResponse,
  UpdateStatusResponse,
} from "@/types";

export const learningPathApi = {
  getLearningPath: () =>
    api.get<LearningPathResponse>("/api/learning-path").then((r) => r.data),

  generatePath: (body: GeneratePathRequest) =>
    api.post<GeneratePathResponse>("/api/learning-path/generate", body).then((r) => r.data),

  getTimeline: () =>
    api.get<TimelineResponse>("/api/learning-path/timeline").then((r) => r.data),

  updatePathStatus: (pathId: string, status: PathStatus) =>
    api
      .put<UpdateStatusResponse>(`/api/learning-path/${pathId}/status`, { status })
      .then((r) => r.data),
};
