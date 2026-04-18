"use client";

import { useEffect } from "react";
import Link from "next/link";

import CourseCatalog from "@/components/course/CourseCatalog";
import TopNav from "@/components/layout/TopNav";
import { buildCatalogPageViewModel } from "@/features/course-platform/presenters";
import { useCourseCatalogStore } from "@/stores/courseCatalogStore";
import { useAuthStore } from "@/stores/authStore";

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
    <>
      <TopNav />
      <main className="min-h-screen px-4 py-8 md:px-6">
        <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
          <section className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">
              {model.catalog.kicker}
            </p>
            <h1 className="text-3xl font-semibold text-slate-950 md:text-4xl">
              {model.hero.title}
            </h1>
            <p className="max-w-3xl text-base leading-7 text-slate-600">
              {model.hero.description}
            </p>
            {model.hero.primaryAction && (
              <Link
                href={model.hero.primaryAction.href}
                className="inline-flex items-center rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                {model.hero.primaryAction.label}
              </Link>
            )}
          </section>

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
        </div>
      </main>
    </>
  );
}
