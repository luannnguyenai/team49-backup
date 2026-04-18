"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function LearnTopicPage() {
  const { topicId } = useParams<{ topicId: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace("/courses/cs231n");
  }, [router, topicId]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center animate-fade-in">
      <div className="text-center space-y-4">
        <div className="h-8 w-8 mx-auto animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Redirecting to course overview...
        </p>
      </div>
    </div>
  );
}
