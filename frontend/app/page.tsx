"use client";

import { useEffect } from "react";
import Link from "next/link";

import CourseCatalog from "@/components/course/CourseCatalog";
import { buildCatalogPageViewModel } from "@/features/course-platform/presenters";
import { useCourseCatalogStore } from "@/stores/courseCatalogStore";
import { useAuthStore } from "@/stores/authStore";
import type { CourseCatalogView } from "@/types";

export default function RootPage() {
  const {
    activeView,
    allCourses,
    recommendedCourses,
    isLoading,
    error,
    hasRecommendations,
    setActiveView,
    loadCatalog,
  } = useCourseCatalogStore();

  const user = useAuthStore((s) => s.user);
  const isAuthenticated = user !== null;

  useEffect(() => {
    loadCatalog({ isAuthenticated });
  }, [isAuthenticated, loadCatalog]);

  const model = buildCatalogPageViewModel({
    user,
    activeView,
    allCourses,
    recommendedCourses,
    hasRecommendations,
  });

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef6ff_55%,#ffffff_100%)] px-4 py-10 md:px-8">
      <div className="mx-auto max-w-6xl space-y-10">
        <section className="grid gap-8 rounded-[32px] bg-[linear-gradient(140deg,#082f49_0%,#0f172a_45%,#f8fafc_100%)] px-8 py-10 text-white shadow-[0_24px_90px_rgba(8,47,73,0.18)] lg:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.8fr)]">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-cyan-200">
              Course-first learning platform
            </p>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-5xl">
                {model.hero.title}
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-200">
                {model.hero.description}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {model.hero.primaryAction && (
                <Link
                  href={model.hero.primaryAction.href}
                  className="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-slate-100"
                >
                  {model.hero.primaryAction.label}
                </Link>
              )}
              <span className="rounded-full border border-white/20 px-4 py-2 text-sm text-slate-100">
                Demo courses: CS231n and CS224n
              </span>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/8 p-6 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/60">
              {model.hero.statusTitle}
            </p>
            <ul className="mt-5 space-y-4 text-sm leading-6 text-slate-200">
              {model.hero.statusItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">
              {model.catalog.kicker}
            </p>
            <h2 className="text-3xl font-semibold text-slate-950">
              {model.catalog.title}
            </h2>
          </div>

          {/* Tab bar — only shown for authenticated users with recommendations */}
          {model.catalog.showTabs && (
            <div
              className="flex gap-1 rounded-full bg-slate-100 p-1"
              role="tablist"
              aria-label="Catalog view"
            >
              {model.catalog.tabs.map((tab) => (
                <button
                  key={tab.key}
                  role="tab"
                  id={`tab-${tab.key}`}
                  aria-selected={activeView === tab.key}
                  aria-controls={`panel-${tab.key}`}
                  onClick={() => setActiveView(tab.key)}
                  className={`flex-1 rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-200 ${
                    activeView === tab.key
                      ? "bg-white text-slate-950 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {isLoading && (
            <div className="card rounded-[28px] p-10 text-center text-sm text-slate-600">
              Loading course catalog...
            </div>
          )}

          {error && (
            <div className="card rounded-[28px] border-red-200 bg-red-50 p-8 text-sm text-red-700">
              {error}
            </div>
          )}

          {!isLoading && !error && (
            <div
              role="tabpanel"
              id={`panel-${activeView}`}
              aria-labelledby={model.catalog.showTabs ? `tab-${activeView}` : undefined}
            >
              <CourseCatalog items={model.catalog.displayedCourses} />
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
