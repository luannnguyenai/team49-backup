import Link from "next/link";
import { Map } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";

export default function EmptyState() {
  const user = useAuthStore((s) => s.user);
  const href = user?.is_onboarded ? "/dashboard" : "/onboarding";
  const label = user?.is_onboarded ? "Choose a course" : "Start onboarding";

  return (
    <div className="flex min-h-80 flex-col items-center justify-center rounded-2xl border p-8 text-center" style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}>
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-900/30">
        <Map className="h-7 w-7" />
      </div>
      <h2 className="mt-4 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
        No learning path yet
      </h2>
      <p className="mt-2 max-w-md text-sm" style={{ color: "var(--text-secondary)" }}>
        Finish onboarding or choose a course so the system can create a personalized learning path for you.
      </p>
      <Link href={href} className="mt-5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:opacity-90">
        {label}
      </Link>
    </div>
  );
}
