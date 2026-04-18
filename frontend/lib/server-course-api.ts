import { cookies } from "next/headers";

import type { CourseOverviewResponse, LearningUnitResponse } from "@/types";

const API_BASE =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export class ServerCourseApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {}

  try {
    const text = await response.text();
    if (text.trim()) return text.trim();
  } catch {}

  return `Request failed (${response.status})`;
}

async function fetchCourseJson<T>(
  path: string,
  options?: {
    auth?: boolean;
    cache?: RequestCache;
  },
): Promise<T> {
  const headers = new Headers({
    Accept: "application/json",
  });

  if (options?.auth) {
    const accessToken = cookies().get("al_access_token")?.value;
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    cache: options?.cache ?? "force-cache",
  });

  if (!response.ok) {
    throw new ServerCourseApiError(response.status, await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

export function fetchCourseOverview(courseSlug: string) {
  return fetchCourseJson<CourseOverviewResponse>(`/api/courses/${courseSlug}/overview`);
}

export function fetchLearningUnit(courseSlug: string, unitSlug: string) {
  return fetchCourseJson<LearningUnitResponse>(
    `/api/courses/${courseSlug}/units/${unitSlug}`,
    {
      auth: true,
      cache: "no-store",
    },
  );
}
