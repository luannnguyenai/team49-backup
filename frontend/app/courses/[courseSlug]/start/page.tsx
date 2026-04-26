"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { courseApi } from "@/lib/api";

interface CourseStartPageProps {
  params: {
    courseSlug: string;
  };
}

export default function CourseStartPage({ params }: CourseStartPageProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function resolveStart() {
      try {
        const decision = await courseApi.start(params.courseSlug);
        if (active) {
          router.replace(decision.target);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to start course.");
        }
      }
    }

    resolveStart();
    return () => {
      active = false;
    };
  }, [params.courseSlug, router]);

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef6ff_100%)] px-4 py-10 md:px-8">
      <div className="mx-auto flex max-w-3xl items-center justify-center">
        <div className="card w-full max-w-lg rounded-[28px] p-10 text-center">
          {error ? (
            <p className="text-sm text-red-700">{error}</p>
          ) : (
            <>
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
              <p className="mt-4 text-sm" style={{ color: "var(--text-secondary)" }}>
                Đang chuẩn bị bài học...
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
