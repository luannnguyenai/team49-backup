"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TutorPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/agent");
  }, [router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <p className="text-sm font-medium text-slate-500">Redirecting to AI Assistant...</p>
    </div>
  );
}
