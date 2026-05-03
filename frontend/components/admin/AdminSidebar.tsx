"use client";

// components/admin/AdminSidebar.tsx
// Vertical nav for /admin. Style matches landing: subtle glass, cyan accent.

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS: { href: string; label: string; icon: string }[] = [
  { href: "/admin", label: "Overview", icon: "◆" },
  { href: "/admin/users", label: "Users", icon: "◉" },
  { href: "/admin/llm", label: "LLM", icon: "✦" },
  { href: "/admin/traffic", label: "Traffic", icon: "↯" },
  { href: "/admin/system", label: "System", icon: "⌬" },
  { href: "/admin/logs", label: "Logs", icon: "≡" },
];

export default function AdminSidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-200/70 bg-white/60 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60 lg:block">
      <div className="sticky top-0 flex h-screen flex-col gap-2 px-4 py-6">
        <div className="mb-6 px-2">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
            Admin Console
          </p>
          <p className="mt-1 bg-gradient-to-r from-indigo-600 via-cyan-500 to-teal-400 bg-clip-text text-lg font-bold text-transparent">
            A20 Dashboard
          </p>
        </div>
        <nav className="flex flex-col gap-1">
          {ITEMS.map((it) => {
            const active = pathname === it.href || (it.href !== "/admin" && pathname.startsWith(it.href));
            return (
              <Link
                key={it.href}
                href={it.href}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-gradient-to-r from-indigo-600/15 via-cyan-500/15 to-teal-400/15 text-slate-900 dark:text-white"
                    : "text-slate-600 hover:bg-white/70 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/70 dark:hover:text-white"
                }`}
              >
                <span className="text-cyan-500">{it.icon}</span>
                {it.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto rounded-xl border border-slate-200/70 bg-white/60 px-3 py-3 text-xs text-slate-500 backdrop-blur dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
          <p className="font-semibold text-slate-700 dark:text-slate-200">Localhost mode</p>
          <p className="mt-1">Grafana → :3001 · Prom → :9090</p>
        </div>
      </div>
    </aside>
  );
}
