"use client";

// app/tutor/page.tsx
// "Current courses" — hub page listing enrolled + recommended courses

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Compass, GraduationCap, PlayCircle } from "lucide-react";
import { historyApi } from "@/lib/api";
import CourseCatalog from "@/components/course/CourseCatalog";
import { buildUserCourseCollections } from "@/features/course-membership/presenters";
import { getCachedAllCourseCatalog } from "@/lib/course-catalog-cache";
import { filterCoursesByQuery, normalizeCourseSearchQuery } from "@/lib/course-search";
import { usePageTitle } from "@/hooks/usePageTitle";
import type { CourseCatalogItem, HistoryItem } from "@/types";

export default function TutorPage() {
  return (
    <Suspense fallback={<TutorPageFallback />}>
      <TutorPageContent />
    </Suspense>
  );
}

function TutorPageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        <p className="text-sm text-text-muted">
          Loading course list...
        </p>
      </div>
    </div>
  );
}

function TutorPageContent() {
  usePageTitle("AI Learning Hub - AI Tutor");
  const searchParams = useSearchParams();
  const [items, setItems] = useState<CourseCatalogItem[]>([]);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [activeUnitSlug, setActiveUnitSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem("al_active_learning_unit");
      if (raw) {
        const parsed = JSON.parse(raw) as { courseSlug?: string; unitSlug?: string };
        if (parsed.courseSlug) setActiveSlug(parsed.courseSlug);
        if (parsed.unitSlug) setActiveUnitSlug(parsed.unitSlug);
      }
    } catch {
      // sessionStorage may be unavailable; ignore and proceed with null.
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getCachedAllCourseCatalog(false),
      historyApi.list({ page_size: 100 }),
    ])
      .then(([catalog, history]) => {
        setItems(catalog.items);
        setHistoryItems(history.items);
      })
      .catch(() => setError("Unable to load the course list. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  const { activeCourse, joinedCourses, recommendedCourses } = buildUserCourseCollections(
    items,
    historyItems,
    activeSlug,
  );
  const rawQuery = searchParams.get("q") ?? "";
  const normalizedQuery = normalizeCourseSearchQuery(rawQuery);
  const hasActiveSearch = normalizedQuery.length >= 2;
  const joinedCourseSlugs = new Set(joinedCourses.map((item) => item.slug));
  const others = items.filter(
    (item) => !joinedCourseSlugs.has(item.slug) && !recommendedCourses.some((course) => course.slug === item.slug),
  );
  const filteredJoinedCourses = filterCoursesByQuery(joinedCourses, rawQuery);
  const filteredRecommendedCourses = filterCoursesByQuery(recommendedCourses, rawQuery);
  const filteredOthers = filterCoursesByQuery(others, rawQuery);
  const hasSearchResults =
    filteredJoinedCourses.length > 0 ||
    filteredRecommendedCourses.length > 0 ||
    filteredOthers.length > 0;
  const hasNothingToShow = joinedCourses.length === 0 && recommendedCourses.length === 0;

  return (
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <header className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300">
          <GraduationCap className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-text-strong">
            Current courses
          </h1>
          <p className="mt-1 text-sm text-text-body">
            Continue your learning path and explore courses recommended for you.
          </p>
        </div>
      </header>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
            <p className="text-sm text-text-muted">
              Loading course list...
            </p>
          </div>
        </div>
      ) : error ? (
        <div className="card flex min-h-40 items-center justify-center">
          <p className="text-sm font-medium text-red-600">{error}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {activeCourse && activeUnitSlug && (
            <section className="flex flex-col gap-4 rounded-2xl border border-border-subtle bg-surface-card p-5 md:flex-row md:items-center md:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-widest text-text-muted">
                  Continue learning
                </p>
                <h2 className="mt-1 truncate text-lg font-bold text-text-strong">
                  {activeCourse.title}
                </h2>
                <p className="mt-1 line-clamp-2 text-sm text-text-body">
                  {activeCourse.short_description}
                </p>
              </div>
              <Link
                href={`/courses/${activeCourse.slug}/learn/${activeUnitSlug}`}
                className="btn-primary flex shrink-0 items-center gap-2"
              >
                <PlayCircle size={16} />
                Resume
              </Link>
            </section>
          )}

          {filteredJoinedCourses.length > 0 && (
            <section className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold text-text-strong">
                  Your courses
                </h2>
                <p className="text-sm text-text-body">
                  Courses you have joined through your learning history.
                </p>
              </div>
              <CourseCatalog items={filteredJoinedCourses} />
            </section>
          )}

          {filteredRecommendedCourses.length > 0 && (
            <section className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold text-text-strong">
                  Recommended for you
                </h2>
                <p className="text-sm text-text-body">
                  Courses that match your personalized learning path.
                </p>
              </div>
              <CourseCatalog items={filteredRecommendedCourses} />
            </section>
          )}

          {hasActiveSearch && !hasSearchResults && (
            <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-border-subtle p-8 text-center text-text-muted">
              No courses matched the keyword &quot;{rawQuery}&quot;.
            </div>
          )}

          {hasNothingToShow && (
            <section className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border-subtle p-10 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300">
                <Compass className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold text-text-strong">
                  No active courses yet
                </p>
                <p className="text-sm text-text-body">
                  Explore the catalog to choose the right course and start learning with AI Tutor.
                </p>
              </div>
              <Link href="/tutor" className="btn-primary inline-flex items-center gap-2">
                <Compass size={16} />
                Explore courses
              </Link>
            </section>
          )}

          {filteredOthers.length > 0 && (
            <div className="pt-2 text-center text-sm text-text-muted">
              There are {filteredOthers.length} more courses in the catalog.{" "}
              <Link
                href="/dashboard"
                className="font-semibold text-primary-600 underline"
              >
                View all
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
