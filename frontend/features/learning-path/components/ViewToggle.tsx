"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import SegmentedControl from "@/components/ui/SegmentedControl";

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
    <SegmentedControl
      ariaLabel="Planner view"
      value={view}
      onChange={onChange}
      options={[
        { value: "graph", label: "Plan" },
        { value: "timeline", label: "Weekly" },
      ]}
      className="w-full sm:w-auto"
    />
  );
}
