"use client";

// app/admin/layout.tsx
// Client-side admin guard + shell. Redirects:
//   - missing JWT  → /login?from=/admin
//   - role !== admin → /tutor

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AdminSidebar from "@/components/admin/AdminSidebar";
import AdminTopbar from "@/components/admin/AdminTopbar";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { useAuthStore } from "@/stores/authStore";
import { tokenStorage } from "@/lib/api";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const router = useRouter();
  const { user, fetchMe } = useAuthStore();

  useEffect(() => {
    const verify = async () => {
      const hasToken = Boolean(tokenStorage.getAccess());
      if (!hasToken) {
        router.replace("/login?from=/admin");
        return;
      }
      let me = user;
      if (!me) {
        await fetchMe();
        me = useAuthStore.getState().user;
      }
      if (!me) {
        router.replace("/login?from=/admin");
        return;
      }
      if (me.role !== "admin") {
        router.replace("/tutor");
        return;
      }
      setChecking(false);
    };
    verify();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.10),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(34,211,238,0.10),_transparent_30%),linear-gradient(180deg,#f8fafc_0%,#ffffff_45%,#ecfeff_100%)]">
      <div className="flex">
        <AdminSidebar />
        <div className="flex min-h-screen flex-1 flex-col">
          <AdminTopbar userEmail={user?.email ?? null} />
          <main className="flex-1 px-6 py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
