"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TutorPage() {
  const router = useRouter();

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem("al_active_learning_unit");
      if (raw) {
        const parsed = JSON.parse(raw) as {
          courseSlug?: string;
          unitSlug?: string;
        };
        if (parsed.courseSlug && parsed.unitSlug) {
          router.replace(`/courses/${parsed.courseSlug}/learn/${parsed.unitSlug}`);
          return;
        }
      }
    } catch {
      // Fall back to the default course overview below.
    }

    router.replace("/courses/cs231n");
  }, [router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center space-y-4">
        <div className="h-8 w-8 mx-auto animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Redirecting to the in-context tutor experience...
        </p>
      </div>
    </div>
  );
}
