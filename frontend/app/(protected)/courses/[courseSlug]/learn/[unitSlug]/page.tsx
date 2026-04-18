"use client";

// app/(protected)/courses/[courseSlug]/learn/[unitSlug]/page.tsx
// Canonical course-first learning page.
// Loads the learning unit payload and renders the unified lecture shell
// with in-context AI Tutor.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import LearningUnitShell from "@/components/learn/LearningUnitShell";
import { courseApi } from "@/lib/api";
import type { LearningUnitResponse } from "@/types";

interface LearningPageProps {
  params: {
    courseSlug: string;
    unitSlug: string;
  };
}

export default function LearningPage({ params }: LearningPageProps) {
  const router = useRouter();
  const [data, setData] = useState<LearningUnitResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadUnit() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await courseApi.learningUnit(
          params.courseSlug,
          params.unitSlug,
        );
        if (active) {
          setData(response);
        }
      } catch (err) {
        if (active) {
          if (
            err &&
            typeof err === "object" &&
            "response" in err &&
            (err as { response?: { status: number } }).response?.status === 404
          ) {
            setError(
              "This learning unit is not available. It may not exist or the course content has not been published yet.",
            );
          } else {
            setError(
              err instanceof Error
                ? err.message
                : "Failed to load learning unit.",
            );
          }
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    loadUnit();
    return () => {
      active = false;
    };
  }, [params.courseSlug, params.unitSlug]);

  useEffect(() => {
    window.sessionStorage.setItem(
      "al_active_learning_unit",
      JSON.stringify({
        courseSlug: params.courseSlug,
        unitSlug: params.unitSlug,
      }),
    );
  }, [params.courseSlug, params.unitSlug]);

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-4.5rem)] items-center justify-center -mx-4 -mt-4 md:-mx-6 md:-mt-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p
            className="text-sm"
            style={{ color: "var(--text-muted)" }}
          >
            Loading learning unit...
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-[calc(100vh-4.5rem)] items-center justify-center -mx-4 -mt-4 md:-mx-6 md:-mt-6">
        <div className="text-center space-y-4 max-w-md px-6">
          <div className="mx-auto h-16 w-16 rounded-full bg-red-50 flex items-center justify-center">
            <svg
              className="h-8 w-8 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v3m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-red-600">
            {error ?? "Content not available."}
          </p>
          <button
            onClick={() => router.push(`/courses/${params.courseSlug}`)}
            className="inline-flex items-center rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            ← Back to course overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="-mx-4 -mt-4 md:-mx-6 md:-mt-6">
      <LearningUnitShell data={data} courseSlug={params.courseSlug} />
    </div>
  );
}
