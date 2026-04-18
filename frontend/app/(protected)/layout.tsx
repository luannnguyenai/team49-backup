"use client";
// app/(protected)/layout.tsx
// Main app layout with top navigation bar. Guards auth + onboarding.

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import { useAuthStore } from "@/stores/authStore";
import { tokenStorage } from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [checking, setChecking] = useState(() => !tokenStorage.getAccess());
  const router = useRouter();
  const { user, fetchMe } = useAuthStore();

  // Client-side auth + onboarding guard
  useEffect(() => {
    const verify = async () => {
      const hasToken = Boolean(tokenStorage.getAccess());
      if (!hasToken) {
        router.replace("/login");
        return;
      }
      setChecking(false);

      // Hydrate user in the background when store was cleared (e.g. hard refresh).
      if (!user) {
        void fetchMe();
      }
    };
    verify();
  }, [fetchMe, router, user]);

  // Redirect if not onboarded (after user is loaded)
  useEffect(() => {
    if (!checking && user && !user.is_onboarded) {
      router.replace("/onboarding");
    }
  }, [checking, user, router]);

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen" style={{ backgroundColor: "var(--bg-page)" }}>
      <TopNav />
      <main className="flex-1 overflow-y-auto p-4 md:p-6 animate-fade-in">
        {children}
      </main>
    </div>
  );
}
