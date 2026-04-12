"use client";
// app/(protected)/layout.tsx
// Main app layout with sidebar + topbar. Guards auth + onboarding.

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { useAuthStore } from "@/stores/authStore";
import { tokenStorage } from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/tutor": "AI Tutor",
  "/learn": "Học tập",
  "/history": "Lịch sử",
  "/profile": "Hồ sơ",
};

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [checking, setChecking] = useState(true);
  const router = useRouter();
  const pathname = usePathname();
  const { user, fetchMe } = useAuthStore();

  // Client-side auth + onboarding guard
  useEffect(() => {
    const verify = async () => {
      const hasToken = Boolean(tokenStorage.getAccess());
      if (!hasToken) {
        router.replace("/login");
        return;
      }
      // Hydrate user if store was cleared (e.g. hard refresh)
      if (!user) await fetchMe();
      setChecking(false);
    };
    verify();
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  // Redirect if not onboarded (after user is loaded)
  useEffect(() => {
    if (!checking && user && !user.is_onboarded) {
      router.replace("/onboarding");
    }
  }, [checking, user, router]);

  const pageTitle =
    PAGE_TITLES[pathname] ??
    Object.entries(PAGE_TITLES).find(([k]) => pathname.startsWith(k))?.[1] ??
    "";

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar title={pageTitle} onMenuClick={() => setMobileOpen(true)} />
        <main
          className="flex-1 overflow-y-auto p-4 md:p-6 animate-fade-in"
          style={{ backgroundColor: "var(--bg-page)" }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
