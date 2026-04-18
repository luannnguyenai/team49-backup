"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import CourseOverview from "@/components/course/CourseOverview";
import { buildUnauthorizedRedirectTarget } from "@/lib/auth-redirect";
import { courseApi } from "@/lib/api";
import type { CourseOverviewResponse } from "@/types";

interface CourseOverviewInteractiveProps {
  courseSlug: string;
  data?: CourseOverviewResponse | null;
  error?: string | null;
}

export default function CourseOverviewInteractive({
  courseSlug,
  data = null,
  error = null,
}: CourseOverviewInteractiveProps) {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const resolvedError = error ?? startError;

  const handleStart = async () => {
    if (!data || data.course.status !== "ready") return;

    setIsStarting(true);
    setStartError(null);
    try {
      const decision = await courseApi.start(data.course.slug);
      if (decision.target) {
        router.push(decision.target);
      }
    } catch (err) {
      if (
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { status: number } }).response?.status === 401
      ) {
        router.push(buildUnauthorizedRedirectTarget(`/courses/${data.course.slug}/start`));
      } else {
        setStartError(err instanceof Error ? err.message : "Failed to start course.");
      }
    } finally {
      setIsStarting(false);
    }
  };

  if (resolvedError || !data) {
    return (
      <div className="card rounded-[28px] border-red-200 bg-red-50 p-8 text-sm text-red-700">
        {resolvedError ?? `Failed to load course overview for '${courseSlug}'.`}
      </div>
    );
  }

  return <CourseOverview data={data} isStarting={isStarting} onStart={handleStart} />;
}
