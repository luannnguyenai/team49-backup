"use client";

interface Props {
  claim: string;
  message: string | null;
  onClaimChange: (claim: string) => void;
  onContinue: () => void;
}

export default function ReplanKnowledgeClaimStep({
  claim,
  message,
  onClaimChange,
  onContinue,
}: Props) {
  return (
    <>
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          What do you already know?
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Specifically describe the parts you've mastered so the system can create a verification assessment. This description does not automatically skip lessons. New assessment results will be used to update your learning path.
        </p>
      </div>

      {message && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
          {message}
        </div>
      )}

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <label
          htmlFor="replan-knowledge-claim"
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          What do you already know?
        </label>
        <textarea
          id="replan-knowledge-claim"
          aria-label="What do you already know?"
          value={claim}
          onChange={(event) => onClaimChange(event.target.value)}
          className="mt-3 min-h-28 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
          }}
          placeholder={"Example:\n- I've mastered CNN, convolution, pooling.\n- I know Faster R-CNN but not sure about YOLO.\n- I understand basic object detection, want to test to skip foundational parts."}
        />
      </div>

      <div className="flex items-center justify-end pt-2">
        <button
          type="button"
          onClick={onContinue}
          className="rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Continue
        </button>
      </div>
    </>
  );
}
