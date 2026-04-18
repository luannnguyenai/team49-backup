"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import CourseOverview from "@/components/course/CourseOverview";
import { courseApi } from "@/lib/api";
import type { CourseOverviewResponse } from "@/types";

interface CourseOverviewPageProps {
  params: {
    courseSlug: string;
  };
}

export default function CourseOverviewPage({ params }: CourseOverviewPageProps) {
  const router = useRouter();
  const [data, setData] = useState<CourseOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await courseApi.overview(params.courseSlug);
        if (active) {
          setData(response);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load course overview.");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    loadOverview();
    return () => {
      active = false;
    };
  }, [params.courseSlug]);

  const handleStart = async () => {
    if (!data || data.course.status !== "ready") return;

    setIsStarting(true);
    try {
      const decision = await courseApi.start(data.course.slug);
      router.push(decision.target);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start course.");
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef6ff_100%)] px-4 py-10 md:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <Link
          href="/"
          className="inline-flex items-center text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
        >
          ← Back to catalog
        </Link>

        {isLoading && (
          <div className="card rounded-[28px] p-10 text-center text-sm text-slate-600">
            Loading course overview...
          </div>
        )}

        {error && (
          <div className="card rounded-[28px] border-red-200 bg-red-50 p-8 text-sm text-red-700">
            {error}
          </div>
        )}

        {data && <CourseOverview data={data} isStarting={isStarting} onStart={handleStart} />}
      </div>
    </main>
  );
}
