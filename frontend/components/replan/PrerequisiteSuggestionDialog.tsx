"use client";

export interface PrerequisiteSuggestion {
  canonicalUnitId: string;
  title: string;
  reason: string;
  depth: number;
}

interface Props {
  suggestions: PrerequisiteSuggestion[];
  onInclude: (suggestions: PrerequisiteSuggestion[]) => void;
  onSkip: () => void;
}

export default function PrerequisiteSuggestionDialog({
  suggestions,
  onInclude,
  onSkip,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Found related foundational topics"
        className="w-full max-w-lg rounded-2xl border bg-white p-5 shadow-xl dark:bg-slate-950"
        style={{ borderColor: "var(--border)" }}
      >
        <div>
          <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
            Found related foundational topics
          </h2>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Some topics you selected typically build on earlier topics in your learning path. These foundational topics haven't been marked as mastered yet. Would you like to add them to your verification assessment?
          </p>
        </div>

        <div className="mt-4 space-y-2">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.canonicalUnitId}
              className="rounded-xl border p-3"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-page)" }}
            >
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {suggestion.title}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                {suggestion.reason}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onSkip}
            className="rounded-xl border-2 px-5 py-2.5 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-primary)",
              backgroundColor: "var(--bg-card)",
            }}
          >
            Skip
          </button>
          <button
            type="button"
            onClick={() => onInclude(suggestions)}
            className="rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
          >
            Add to assessment
          </button>
        </div>
      </section>
    </div>
  );
}
