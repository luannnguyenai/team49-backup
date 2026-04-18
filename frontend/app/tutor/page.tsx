"use client";

// app/tutor/page.tsx
// "Khoá học đang tham gia" — hub page listing enrolled + recommended courses

import { GraduationCap } from "lucide-react";

export default function TutorPage() {
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

      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Đang tải danh sách khoá học...
          </p>
        </div>
      </div>
    </div>
  );
}
