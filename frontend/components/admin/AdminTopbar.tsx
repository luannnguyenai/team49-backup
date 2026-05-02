"use client";

// components/admin/AdminTopbar.tsx

import Link from "next/link";
import { usePathname } from "next/navigation";

const TITLES: Record<string, string> = {
  "/admin": "Overview",
  "/admin/users": "Users",
  "/admin/llm": "LLM Observability",
  "/admin/traffic": "API Traffic",
  "/admin/system": "System Health",
  "/admin/logs": "Logs",
};

export default function AdminTopbar({ userEmail }: { userEmail?: string | null }) {
  const pathname = usePathname();
  const title = TITLES[pathname] ?? "Admin";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/70 bg-white/70 px-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/70">
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
        >
          ← App
        </Link>
        <span className="hidden text-slate-300 sm:inline">/</span>
        <h1 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-white">
          {title}
        </h1>
      </div>
      <div className="flex items-center gap-4 text-sm">
        {userEmail && (
          <span className="hidden rounded-full bg-gradient-to-r from-indigo-600/10 via-cyan-500/10 to-teal-400/10 px-3 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 sm:inline">
            {userEmail}
          </span>
        )}
      </div>
    </header>
  );
}
