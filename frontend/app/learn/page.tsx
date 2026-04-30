import type { Metadata } from "next";
import { Suspense } from "react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import LearningPathShell from "@/features/learning-path/components/LearningPathShell";

export const metadata: Metadata = { title: "Learning Path" };

export default function LearnPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-40 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <LearningPathShell />
    </Suspense>
  );
}
