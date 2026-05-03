"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { MessageSquareText } from "lucide-react";

export default function TutorPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/agent");
  }, [router]);

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-3xl flex-col items-center justify-center px-6 text-center animate-fade-in">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-accent-soft text-primary-700 dark:text-primary-300">
        <MessageSquareText className="h-6 w-6" />
      </div>
      <h1 className="text-2xl font-bold text-text-strong">AI Assistant</h1>
      <p className="mt-2 text-sm text-text-body">
        Redirecting to the course-first assistant experience...
      </p>
    </div>
  );
}
