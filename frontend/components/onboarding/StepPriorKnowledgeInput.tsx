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
          Nền tảng hiện tại của bạn
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Nhập thủ công vài dòng. Khi bấm tiếp tục, AI sẽ suy nghĩ và lọc ra một shortlist
          ngắn để bạn xác nhận ở bước sau.
        </p>
      </div>

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <label
          htmlFor="prior-knowledge"
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Kiến thức bạn đã học
        </label>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Ví dụ: {GOAL_PRIOR_HINTS[goalId].join(", ")}. Có thể ghi cả thời gian đã học AI.
        </p>
        <textarea
          id="prior-knowledge"
          aria-label="Kiến thức bạn đã học"
          value={priorKnowledgeText}
          onChange={(event) => onPriorKnowledgeChange(event.target.value)}
          className="mt-3 min-h-24 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
          }}
          placeholder="Tôi đã học CNN, ResNet, transformer khoảng 3 tháng..."
        />
      </div>

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <label
          htmlFor="coding-experience"
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Kỹ năng coding ML
        </label>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          Gợi ý: {CODING_HINTS.join(", ")}.
        </p>
        <textarea
          id="coding-experience"
          aria-label="Kỹ năng coding ML"
          value={codingExperienceText}
          onChange={(event) => onCodingExperienceChange(event.target.value)}
          className="mt-3 min-h-20 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
          }}
          placeholder="Python ổn, PyTorch mới code model cơ bản, chưa quen HuggingFace..."
        />
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
          Quay lại
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={isAnalyzing}
          className="ml-auto inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-75"
        >
          {isAnalyzing && <Loader2 className="h-4 w-4 animate-spin" />}
          {isAnalyzing ? "AI thinking..." : "Tiếp tục"}
        </button>
      </div>
    </div>
  );
}

