"use client";

import { BookOpen, Lightbulb } from "lucide-react";

import BottomSheet from "@/components/ui/BottomSheet";

type ChapterView = {
  id: string;
  title: string;
  timestamp: string;
  start_time: number;
  key_takeaways: string[];
};

type MobileKeyIdeasSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  activeChapter: ChapterView | null;
  chapters: ChapterView[];
  currentTimeLabel: string;
  durationLabel: string;
  onSeek: (seconds: number) => void;
};

export default function MobileKeyIdeasSheet({
  open,
  onOpenChange,
  activeChapter,
  chapters,
  currentTimeLabel,
  durationLabel,
  onSeek,
}: MobileKeyIdeasSheetProps) {
  return (
    <BottomSheet open={open} onOpenChange={onOpenChange} title="Key ideas">
      <div className="space-y-5">
        {activeChapter?.key_takeaways.length ? (
          <section className="rounded-2xl border px-4 py-4" style={{ borderColor: "var(--border)" }}>
            <div className="mb-3 flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-100 text-amber-500 shadow-sm">
                <Lightbulb className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest-sm text-amber-600">
                  IDEA
                </p>
                <h2 className="mt-1 text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                  Key ideas at this moment
                </h2>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  {activeChapter.title}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {activeChapter.key_takeaways.map((takeaway) => (
                <div
                  key={takeaway}
                  className="flex items-start gap-3 rounded-2xl border border-amber-200/70 bg-amber-50/70 px-4 py-3"
                >
                  <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                  <p className="text-sm leading-6" style={{ color: "var(--text-primary)" }}>
                    {takeaway}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {chapters.length ? (
          <section className="rounded-2xl border px-4 py-4" style={{ borderColor: "var(--border)" }}>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest-sm text-blue-600">
                  Timestamps
                </p>
                <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
                  Jump quickly between sections of the video
                </p>
              </div>
              <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
                {currentTimeLabel} / {durationLabel}
              </span>
            </div>

            <div className="space-y-2">
              {chapters.map((chapter) => {
                const isActive = activeChapter?.id === chapter.id;

                return (
                  <button
                    key={chapter.id}
                    type="button"
                    onClick={() => {
                      onSeek(chapter.start_time);
                      onOpenChange(false);
                    }}
                    className="flex w-full items-start gap-4 rounded-2xl border px-4 py-3 text-left transition-colors"
                    style={{
                      borderColor: isActive ? "rgba(37,99,235,0.28)" : "var(--border)",
                      backgroundColor: isActive ? "rgba(37,99,235,0.08)" : "transparent",
                    }}
                  >
                    <span className="shrink-0 font-mono text-sm text-blue-600">
                      {chapter.timestamp}
                    </span>
                    <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                      {chapter.title}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        ) : null}
      </div>
    </BottomSheet>
  );
}
