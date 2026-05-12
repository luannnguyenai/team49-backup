"use client";

import Link from "next/link";
import { CheckCircle2 } from "lucide-react";

import BottomSheet from "@/components/ui/BottomSheet";
import type { CourseUnitListItem } from "@/types";

type MobileLessonSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lectures: CourseUnitListItem[];
  courseSlug: string;
  activeLectureOrder: number | null | undefined;
  activeUnitSlug: string;
  formatLectureLabel: (orderIndex: number, fallback?: string | null) => string;
};

export default function MobileLessonSheet({
  open,
  onOpenChange,
  lectures,
  courseSlug,
  activeLectureOrder,
  activeUnitSlug,
  formatLectureLabel,
}: MobileLessonSheetProps) {
  return (
    <BottomSheet open={open} onOpenChange={onOpenChange} title="Lessons">
      <div className="space-y-2">
        {lectures.map((lecture) => {
          const isActive = lecture.order_index === activeLectureOrder || lecture.slug === activeUnitSlug;

          return (
            <Link
              key={`${lecture.order_index}-${lecture.slug}`}
              href={`/courses/${courseSlug}/learn/${lecture.slug}`}
              onClick={() => onOpenChange(false)}
              className="block rounded-2xl border px-4 py-3 transition-colors"
              style={{
                borderColor: isActive ? "rgba(37,99,235,0.28)" : "var(--border)",
                backgroundColor: isActive ? "rgba(37,99,235,0.08)" : "transparent",
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-[11px] font-semibold uppercase tracking-widest-sm text-blue-600">
                  {formatLectureLabel(lecture.order_index, lecture.lecture_label)}
                </p>
                {lecture.is_completed ? (
                  <span
                    aria-label={`${formatLectureLabel(lecture.order_index, lecture.lecture_label)} completed`}
                    className="text-emerald-500"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                {lecture.title}
              </p>
            </Link>
          );
        })}
      </div>
    </BottomSheet>
  );
}
