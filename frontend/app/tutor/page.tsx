"use client";

// app/tutor/page.tsx
// "Khoá học đang tham gia" — hub page listing enrolled + recommended courses

import { useEffect, useState } from "react";
import Link from "next/link";
import { GraduationCap, PlayCircle } from "lucide-react";
import { courseApi } from "@/lib/api";
import type { CourseCatalogItem } from "@/types";

interface CatalogSplit {
  enrolled: CourseCatalogItem[];
  recommended: CourseCatalogItem[];
  others: CourseCatalogItem[];
}

function splitCatalog(items: CourseCatalogItem[], activeSlug: string | null): CatalogSplit {
  const enrolled: CourseCatalogItem[] = [];
  const recommended: CourseCatalogItem[] = [];
  const others: CourseCatalogItem[] = [];
  for (const item of items) {
    if (activeSlug && item.slug === activeSlug) enrolled.push(item);
    else if (item.is_recommended) recommended.push(item);
    else others.push(item);
  }
  return { enrolled, recommended, others };
}

export default function TutorPage() {
  const [items, setItems] = useState<CourseCatalogItem[]>([]);
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
    courseApi
      .catalog({ view: "all", includeUnavailable: false })
      .then((res) => setItems(res.items))
      .catch(() => setError("Không thể tải danh sách khoá học. Vui lòng thử lại."))
      .finally(() => setLoading(false));
  }, []);

  const { enrolled, recommended, others } = splitCatalog(items, activeSlug);

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
          {enrolled.length > 0 && activeUnitSlug && (
            <section
              className="flex flex-col gap-4 rounded-2xl border p-5 md:flex-row md:items-center md:justify-between"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
                  Tiếp tục học
                </p>
                <h2 className="mt-1 truncate text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                  {enrolled[0].title}
                </h2>
                <p className="mt-1 line-clamp-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                  {enrolled[0].short_description}
                </p>
              </div>
              <Link
                href={`/courses/${enrolled[0].slug}/learn/${activeUnitSlug}`}
                className="btn-primary flex shrink-0 items-center gap-2"
              >
                <PlayCircle size={16} />
                Tiếp tục
              </Link>
            </section>
          )}

          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            {`Tìm thấy ${items.length} khoá · ${enrolled.length} đang tham gia · ${recommended.length} gợi ý · ${others.length} khác.`}
          </div>
        </div>
      )}
    </div>
  );
}
