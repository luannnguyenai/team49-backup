"use client";

import { BookOpen, Lightbulb, Sparkles } from "lucide-react";

type MobileStudyToolbarProps = {
  tutorEnabled: boolean;
  onOpenLessons: () => void;
  onOpenTutor: () => void;
  onOpenKeyIdeas: () => void;
};

export default function MobileStudyToolbar({
  tutorEnabled,
  onOpenLessons,
  onOpenTutor,
  onOpenKeyIdeas,
}: MobileStudyToolbarProps) {
  return (
    <div className="mobile-sticky-footer sticky bottom-0 z-20 -mx-1 mt-4 rounded-[1.75rem] border border-[color:var(--border)] bg-[color:var(--bg-card)]/95 px-3 pt-3 shadow-[0_-12px_30px_rgba(15,23,42,0.12)] backdrop-blur md:hidden">
      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl border border-[color:var(--border)] bg-[color:var(--bg-elevated)] px-3 py-2 text-xs font-semibold text-[color:var(--text-primary)]"
          onClick={onOpenLessons}
        >
          <BookOpen className="h-4 w-4 text-blue-600" />
          Lessons
        </button>
        <button
          type="button"
          className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl border border-[color:var(--border)] bg-[color:var(--bg-elevated)] px-3 py-2 text-xs font-semibold text-[color:var(--text-primary)] disabled:opacity-50"
          disabled={!tutorEnabled}
          onClick={onOpenTutor}
        >
          <Sparkles className="h-4 w-4 text-amber-500" />
          Tutor
        </button>
        <button
          type="button"
          className="flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl border border-[color:var(--border)] bg-[color:var(--bg-elevated)] px-3 py-2 text-xs font-semibold text-[color:var(--text-primary)]"
          onClick={onOpenKeyIdeas}
        >
          <Lightbulb className="h-4 w-4 text-amber-500" />
          Key ideas
        </button>
      </div>
    </div>
  );
}
