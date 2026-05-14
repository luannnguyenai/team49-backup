"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { useRouter } from "next/navigation";

import BottomSheet from "@/components/ui/BottomSheet";
import { getCachedAllCourseCatalog } from "@/lib/course-catalog-cache";
import { filterCoursesByQuery, normalizeCourseSearchQuery } from "@/lib/course-search";
import type { CourseCatalogItem } from "@/types";

const MIN_SEARCH_QUERY_LENGTH = 2;
const MAX_RESULTS = 8;

type MobileSearchSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  catalogCacheScope?: string;
};

export default function MobileSearchSheet({
  open,
  onOpenChange,
  catalogCacheScope = "public",
}: MobileSearchSheetProps) {
  const router = useRouter();
  const mountedRef = useRef(true);
  const [query, setQuery] = useState("");
  const [catalogCourses, setCatalogCourses] = useState<CourseCatalogItem[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [hasLoadedCourses, setHasLoadedCourses] = useState(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    setCatalogCourses([]);
    setHasLoadedCourses(false);
  }, [catalogCacheScope]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }

    if (hasLoadedCourses || isLoadingCourses) {
      return;
    }

    setIsLoadingCourses(true);
    getCachedAllCourseCatalog(true, catalogCacheScope)
      .then((response) => {
        if (mountedRef.current) {
          setCatalogCourses(response.items);
          setHasLoadedCourses(true);
        }
      })
      .catch(() => {
        if (mountedRef.current) {
          setCatalogCourses([]);
          setHasLoadedCourses(false);
        }
      })
      .finally(() => {
        if (mountedRef.current) {
          setIsLoadingCourses(false);
        }
      });
  }, [catalogCacheScope, hasLoadedCourses, isLoadingCourses, open]);

  const matchingCourses = useMemo(() => {
    const normalizedQuery = normalizeCourseSearchQuery(query);
    if (normalizedQuery.length < MIN_SEARCH_QUERY_LENGTH) {
      return [];
    }
    return filterCoursesByQuery(catalogCourses, query).slice(0, MAX_RESULTS);
  }, [catalogCourses, query]);

  const routeToCourse = (courseSlug: string) => {
    onOpenChange(false);
    setQuery("");
    router.push(`/courses/${courseSlug}`);
  };

  return (
    <BottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="Search courses"
      description="Find the next course to study without squeezing the desktop search bar onto a phone screen."
      panelClassName="mobile-sheet-panel sm:rounded-[1.75rem]"
    >
      <div className="space-y-4 pt-3">
        <label
          className="flex items-center gap-2 rounded-full border px-3 py-3"
          style={{ backgroundColor: "var(--bg-page)", borderColor: "var(--border)" }}
        >
          <Search className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
          <input
            aria-label="Search courses"
            placeholder="Search by course title, description..."
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
            }}
            className="w-full bg-transparent text-sm outline-none placeholder:text-[color:var(--text-muted)]"
            style={{ color: "var(--text-primary)" }}
          />
          {query ? (
            <button
              type="button"
              aria-label="Clear search query"
              className="flex h-6 w-6 items-center justify-center rounded-full transition-colors hover:bg-slate-200 dark:hover:bg-slate-700"
              onClick={() => setQuery("")}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : null}
        </label>

        {isLoadingCourses ? (
          <p className="text-sm text-text-body">Loading courses...</p>
        ) : matchingCourses.length > 0 ? (
          <ul className="space-y-2">
            {matchingCourses.map((course) => (
              <li key={course.id}>
                <button
                  type="button"
                  className="flex w-full flex-col items-start gap-1 rounded-2xl border border-[color:var(--border-subtle)] bg-[color:var(--surface-card)] px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-900"
                  onClick={() => routeToCourse(course.slug)}
                >
                  <span className="text-sm font-semibold text-text-strong">{course.title}</span>
                  <span className="text-xs leading-5 text-text-body">{course.short_description}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : query ? (
          <p className="text-sm text-text-body">No matching courses found.</p>
        ) : (
          <p className="text-sm text-text-body">Search by title, description, or topic.</p>
        )}
      </div>
    </BottomSheet>
  );
}
