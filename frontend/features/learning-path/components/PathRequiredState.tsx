"use client";

import Link from "next/link";
import { ArrowRight, MapIcon } from "lucide-react";
import { createLearningProfileForPath } from "../profile";
import { useLearningPathStore } from "../store";

export default function PathRequiredState() {
  const setProfile = useLearningPathStore((state) => state.setProfile);

  const choosePath = (pathKey: "computer_vision" | "nlp") => {
    setProfile(
      createLearningProfileForPath(pathKey, {
        weeklyHours: null,
        source: "manual",
      }),
    );
  };

  return (
    <div
      className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border p-8 text-center"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-100 text-primary-700">
        <MapIcon className="h-7 w-7" />
      </div>
      <h2 className="mt-5 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        Choose a path before you start learning
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
        Planner V1 only renders a concrete path. Choose either Computer Vision or NLP.
      </p>
      <div className="mt-6 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => choosePath("computer_vision")}
          className="rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Computer Vision
          </span>
          <span className="mt-1 block text-xs" style={{ color: "var(--text-secondary)" }}>
            CS230 → CS231n
          </span>
        </button>
        <button
          type="button"
          onClick={() => choosePath("nlp")}
          className="rounded-2xl border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            Natural Language Processing
          </span>
          <span className="mt-1 block text-xs" style={{ color: "var(--text-secondary)" }}>
            CS230 → CS224n
          </span>
        </button>
      </div>
      <Link
        href="/onboarding?next=/learn"
        className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary-600 underline-offset-4 hover:underline"
      >
        Go to full onboarding
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
