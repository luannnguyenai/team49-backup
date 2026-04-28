"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

export type LearnView = "graph" | "timeline";

const STORAGE_KEY = "learn:view";

function getInitialView(searchValue: string | null): LearnView {
  if (searchValue === "graph" || searchValue === "timeline") return searchValue;
  if (typeof window === "undefined") return "graph";
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved === "graph" || saved === "timeline") return saved;
  return window.matchMedia("(max-width: 767px)").matches ? "timeline" : "graph";
}

export function usePersistedLearnView(): [LearnView, (view: LearnView) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [view, setViewState] = useState<LearnView>(() => getInitialView(searchParams.get("view")));

  useEffect(() => {
    setViewState(getInitialView(searchParams.get("view")));
  }, [searchParams]);

  const setView = (next: LearnView) => {
    setViewState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", next);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  return [view, setView];
}

export default function ViewToggle({ view, onChange }: { view: LearnView; onChange: (view: LearnView) => void }) {
  return (
    <div className="flex rounded-xl p-1" style={{ backgroundColor: "var(--bg-page)" }}>
      {([
        ["graph", "Plan"],
        ["timeline", "Tuần"],
      ] as const).map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={cn(
            "rounded-lg px-4 py-1.5 text-sm font-medium transition-colors",
            view === key ? "bg-white text-primary-600 shadow-sm dark:bg-slate-800" : "hover:bg-white/60 dark:hover:bg-slate-800/60",
          )}
          style={view !== key ? { color: "var(--text-secondary)" } : undefined}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
