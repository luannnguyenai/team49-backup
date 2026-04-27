"use client";

import Link from "next/link";
import { ArrowRight, MapIcon } from "lucide-react";

export default function PathRequiredState() {
  return (
    <div
      className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border p-8 text-center"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 dark:bg-primary-950/40 dark:text-primary-300">
        <MapIcon className="h-7 w-7" />
      </div>
      <h2 className="mt-5 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        Chọn lộ trình trước khi học
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-6" style={{ color: "var(--text-secondary)" }}>
        Planner V1 chỉ render lộ trình cụ thể. Hãy chọn một path: Deep Learning → Computer Vision hoặc Deep Learning → NLP.
      </p>
      <Link
        href="/onboarding?next=/learn"
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-700"
      >
        Chọn path học
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
