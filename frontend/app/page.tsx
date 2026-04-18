"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import CourseCatalog from "@/components/course/CourseCatalog";
import { courseApi } from "@/lib/api";
import type { CourseCatalogItem } from "@/types";

export default function RootPage() {
  const [courses, setCourses] = useState<CourseCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadCatalog() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await courseApi.catalog({
          view: "all",
          includeUnavailable: true,
        });
        if (active) {
          setCourses(response.items);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load course catalog.");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    loadCatalog();
    return () => {
      active = false;
    };
  }, []);

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
                Start from the catalog, then move into a guided lecture experience with AI Tutor in context.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-200">
                The home landing now surfaces every public course. Ready courses open into overview and learning flow.
                Upcoming courses stay visible so the platform can grow without breaking the contract.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/login"
                className="inline-flex items-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-slate-100"
              >
                Sign in to continue
              </Link>
              <span className="rounded-full border border-white/20 px-4 py-2 text-sm text-slate-100">
                Demo courses: CS231n and CS224n
              </span>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-white/8 p-6 backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/60">
              Current rollout rules
            </p>
            <ul className="mt-5 space-y-4 text-sm leading-6 text-slate-200">
              <li>CS231n is the only learnable demo course in this phase.</li>
              <li>CS224n stays visible with a consistent coming-soon state.</li>
              <li>Start learning routes into auth and onboarding gates before the protected flow.</li>
            </ul>
          </div>
        </section>

        <section className="space-y-5">
          <div className="space-y-2">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">
              Public catalog
            </p>
            <h2 className="text-3xl font-semibold text-slate-950">Explore available courses</h2>
          </div>

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

          {!isLoading && !error && <CourseCatalog items={courses} />}
        </section>
      </div>
    </main>
  );
}
