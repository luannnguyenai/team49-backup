"use client";

// app/tutor/page.tsx
// "Khoá học đang tham gia" — hub page listing enrolled + recommended courses

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Compass, GraduationCap, PlayCircle } from "lucide-react";
import { historyApi } from "@/lib/api";
import CourseCatalog from "@/components/course/CourseCatalog";
import { buildUserCourseCollections } from "@/features/course-membership/presenters";
import { getCachedAllCourseCatalog } from "@/lib/course-catalog-cache";
import { filterCoursesByQuery, normalizeCourseSearchQuery } from "@/lib/course-search";
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
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Đang tải danh sách khoá học...
        </p>
      </div>
    </div>
  );
}

function TutorPageContent() {
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
      .catch(() => setError("Không thể tải danh sách khoá học. Vui lòng thử lại."))
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
    <div className="space-y-8 animate-fade-in">
      <header className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-100 text-primary-600 dark:bg-primary-900/30">
          <GraduationCap className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            Khoá học đang tham gia
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            Tiếp tục lộ trình học và khám phá các khoá được gợi ý cho bạn.
          </p>
        </div>
      </header>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Đang tải danh sách khoá học...
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
            <section
              className="flex flex-col gap-4 rounded-2xl border p-5 md:flex-row md:items-center md:justify-between"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  Tiếp tục học
                </p>
                <h2 className="mt-1 truncate text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                  {activeCourse.title}
                </h2>
                <p className="mt-1 line-clamp-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                  {activeCourse.short_description}
                </p>
              </div>
              <Link
                href={`/courses/${activeCourse.slug}/learn/${activeUnitSlug}`}
                className="btn-primary flex shrink-0 items-center gap-2"
              >
                <PlayCircle size={16} />
                Tiếp tục
              </Link>
            </section>
          )}

          {filteredJoinedCourses.length > 0 && (
            <section className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                  Khoá của bạn
                </h2>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  Các khoá bạn đã tham gia qua lịch sử học tập.
                </p>
              </div>
              <CourseCatalog items={filteredJoinedCourses} />
            </section>
          )}

          {filteredRecommendedCourses.length > 0 && (
            <section className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                  Gợi ý cho bạn
                </h2>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  Khoá phù hợp với lộ trình cá nhân hoá.
                </p>
              </div>
              <CourseCatalog items={filteredRecommendedCourses} />
            </section>
          )}

          {hasActiveSearch && !hasSearchResults && (
            <div
              className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed p-8 text-center"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
            >
              Không tìm thấy khóa học phù hợp với từ khóa &quot;{rawQuery}&quot;.
            </div>
          )}

          {hasNothingToShow && (
            <section
              className="flex flex-col items-center gap-4 rounded-2xl border border-dashed p-10 text-center"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900/30">
                <Compass className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
                  Chưa có khoá nào đang tham gia
                </p>
                <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                  Khám phá danh mục để chọn khoá phù hợp và bắt đầu học cùng AI Tutor.
                </p>
              </div>
              <Link href="/tutor" className="btn-primary inline-flex items-center gap-2">
                <Compass size={16} />
                Khám phá khoá học
              </Link>
            </section>
          )}

          {filteredOthers.length > 0 && (
            <div className="pt-2 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              Còn {filteredOthers.length} khoá khác trong danh mục.{" "}
              <Link
                href="/tutor"
                className="font-semibold underline"
                style={{ color: "var(--color-primary-600)" }}
              >
                Xem tất cả
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
