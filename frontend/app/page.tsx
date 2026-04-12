// app/page.tsx
// Root page — client-side redirect based on auth state

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { tokenStorage } from "@/lib/api";

export default function RootPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    const hasToken = Boolean(tokenStorage.getAccess());
    if (!hasToken) {
      router.replace("/login");
    } else if (!user?.is_onboarded) {
      router.replace("/onboarding");
    } else {
      router.replace("/dashboard");
    }
  }, [user, router]);

  return null;
}
