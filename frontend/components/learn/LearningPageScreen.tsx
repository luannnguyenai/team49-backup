"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import LearningUnitShell from "@/components/learn/LearningUnitShell";
import type { LearningUnitResponse } from "@/types";

interface LearningPageScreenProps {
  courseSlug: string;
  unitSlug: string;
  data?: LearningUnitResponse | null;
  error?: string | null;
}

export default function LearningPageScreen({
  courseSlug,
  unitSlug,
  data = null,
  error = null,
}: LearningPageScreenProps) {
  const router = useRouter();

  useEffect(() => {
    if (!data) return;

    window.sessionStorage.setItem(
      "al_active_learning_unit",
      JSON.stringify({
        courseSlug,
        unitSlug,
      }),
    );
  }, [courseSlug, data, unitSlug]);

  if (error || !data) {
    return (
      <div className="flex h-[calc(100vh-4.5rem)] items-center justify-center -mx-4 -mt-4 md:-mx-6 md:-mt-6">
        <div className="text-center space-y-4 max-w-md px-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-50">
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
            onClick={() => router.push(`/courses/${courseSlug}`)}
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
      <LearningUnitShell data={data} courseSlug={courseSlug} />
    </div>
  );
}
