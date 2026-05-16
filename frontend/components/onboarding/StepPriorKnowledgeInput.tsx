"use client";

import { Loader2 } from "lucide-react";
import type { PlannerGoalId } from "./priorCandidateBuilder";

interface Props {
  goalId: PlannerGoalId;
  priorKnowledgeText: string;
  codingExperienceText: string;
  isAnalyzing: boolean;
  onPriorKnowledgeChange: (value: string) => void;
  onCodingExperienceChange: (value: string) => void;
  onBack: () => void;
  onNext: () => void;
}

const GOAL_PRIOR_HINTS: Record<PlannerGoalId, string[]> = {
  computer_vision: [
    "CNN / ResNet / ViT",
    "object detection",
    "segmentation",
    "generative vision",
  ],
  nlp: [
    "word vectors",
    "RNN / seq2seq",
    "attention / transformer",
    "LLM agents",
  ],
};

const CODING_HINTS = ["Python", "PyTorch", "HuggingFace", "training loop", "debug model"];

const CODING_LEVELS = [
  {
    label: "Beginner",
    value:
      "Beginner: basic Python knowledge, limited ML coding experience, little or no PyTorch/HuggingFace practice.",
    description: "Basic Python, little ML coding.",
  },
  {
    label: "Intermediate",
    value:
      "Intermediate: comfortable with Python and basic PyTorch training/debugging, but not advanced production ML tooling.",
    description: "Can train/debug basic PyTorch models.",
  },
  {
    label: "Advanced",
    value:
      "Advanced: comfortable building, training, debugging, and adapting ML models with PyTorch/HuggingFace and related tooling.",
    description: "Comfortable with model training and tooling.",
  },
] as const;

export default function StepPriorKnowledgeInput({
  goalId,
  priorKnowledgeText,
  codingExperienceText,
  isAnalyzing,
  onPriorKnowledgeChange,
  onCodingExperienceChange,
  onBack,
  onNext,
}: Props) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Your current foundation
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Enter a few lines manually. When you continue, AI will reason over it and create
          a short shortlist for you to confirm in the next step.
        </p>
      </div>

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <label
          htmlFor="prior-knowledge"
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Knowledge you have studied
        </label>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Example: {GOAL_PRIOR_HINTS[goalId].join(", ")}. You can also mention how long you have studied AI.
        </p>
        <textarea
          id="prior-knowledge"
          aria-label="Knowledge you have studied"
          value={priorKnowledgeText}
          onChange={(event) => onPriorKnowledgeChange(event.target.value)}
          className="mt-3 min-h-24 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
          }}
          placeholder="I have studied CNN, ResNet, and transformers for about 3 months..."
        />
      </div>

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          ML coding skill
        </p>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Hints: {CODING_HINTS.join(", ")}.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {CODING_LEVELS.map((level) => {
            const isSelected = codingExperienceText === level.value;
            return (
              <button
                key={level.label}
                type="button"
                aria-label={`${level.label} coding skill`}
                onClick={() => onCodingExperienceChange(level.value)}
                className={`rounded-xl border-2 p-3 text-left transition-all ${
                  isSelected
                    ? "border-primary-600 bg-primary-50 text-primary-700"
                    : "hover:border-slate-300"
                }`}
                style={{
                  borderColor: isSelected ? undefined : "var(--border)",
                  backgroundColor: isSelected ? undefined : "var(--bg-card)",
                }}
              >
                <span className="block text-sm font-semibold">{level.label}</span>
                <span className="mt-1 block text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {level.description}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          disabled={isAnalyzing}
          className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            borderColor: "var(--border)",
            color: "var(--text-primary)",
            backgroundColor: "var(--bg-card)",
          }}
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={isAnalyzing}
          className="ml-auto inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-75"
        >
          {isAnalyzing && <Loader2 className="h-4 w-4 animate-spin" />}
          {isAnalyzing ? "AI thinking..." : "Continue"}
        </button>
      </div>
    </div>
  );
}
