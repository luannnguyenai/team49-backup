"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { useRouter } from "next/navigation";

import ReplanKnowledgeClaimStep from "@/components/replan/ReplanKnowledgeClaimStep";
import PrerequisiteSuggestionDialog, { type PrerequisiteSuggestion } from "@/components/replan/PrerequisiteSuggestionDialog";
import ReplanScopeReviewStep, {
  type ReplanReviewUnit,
  type ReplanSelectedAssessmentUnit,
} from "@/components/replan/ReplanScopeReviewStep";
import { buildReplanAssessmentHref, writeReplanAssessmentContext } from "@/lib/replan-assessment-context";
import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";

const demoScopeUnits: ReplanReviewUnit[] = [
  {
    canonicalUnitId: "unit_faster_rcnn",
    title: "Faster R-CNN",
    source: "matched_from_description",
    knowledgePoints: ["Region Proposal Network", "Anchor boxes", "Two-stage detection", "RoI pooling / feature extraction"],
    questionCounts: { easy: 3, medium: 4, hard: 2, application: 1 },
  },
];

const demoPrerequisites: (PrerequisiteSuggestion & { reviewUnit: ReplanReviewUnit })[] = [
  {
    canonicalUnitId: "unit_rcnn",
    title: "R-CNN",
    reason: "R-CNN is a foundation for Faster R-CNN in the current path.",
    depth: 1,
    reviewUnit: {
      canonicalUnitId: "unit_rcnn",
      title: "R-CNN",
      source: "suggested_prerequisite",
      suggestedForTitle: "Faster R-CNN",
      knowledgePoints: ["Region proposals", "Selective search"],
      questionCounts: { easy: 2, medium: 3, hard: 1, application: 0 },
    },
  },
];

export default function ReplanPage() {
  const router = useRouter();
  const [claim, setClaim] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [step, setStep] = useState<"describe" | "review">("describe");
  const [reviewUnits, setReviewUnits] = useState<ReplanReviewUnit[]>(demoScopeUnits);
  const [showPrerequisites, setShowPrerequisites] = useState(false);

  function continueToAnalysis() {
    const validation = validateReplanKnowledgeClaim(claim);
    if (!validation.ok) {
      setMessage(validation.message);
      return;
    }
    if (/already\s+mastered|đã\s+nắm\s+rõ/i.test(claim) && /faster\s+r-?cnn/i.test(claim)) {
      setMessage("Faster R-CNN đã được ghi nhận là bạn nắm rõ rồi, nên không cần test lại.");
      setReviewUnits([]);
      setShowPrerequisites(false);
      setStep("review");
      return;
    }
    setMessage(validation.warning ?? null);
    setReviewUnits(demoScopeUnits);
    setShowPrerequisites(demoPrerequisites.length > 0);
    setStep("review");
  }

  function describeAgain() {
    setStep("describe");
    setShowPrerequisites(false);
  }

  function includePrerequisites(suggestions: PrerequisiteSuggestion[]) {
    const suggestionIds = new Set(suggestions.map((suggestion) => suggestion.canonicalUnitId));
    setReviewUnits([
      ...demoScopeUnits,
      ...demoPrerequisites
        .filter((suggestion) => suggestionIds.has(suggestion.canonicalUnitId))
        .map((suggestion) => suggestion.reviewUnit),
    ]);
    setShowPrerequisites(false);
  }

  function startAssessment(selectedUnits: ReplanSelectedAssessmentUnit[]) {
    writeReplanAssessmentContext({
      units: selectedUnits.map((unit) => ({
        canonicalUnitId: unit.canonicalUnitId,
        title: unit.title,
        difficultyFilter: unit.difficultyFilter,
        selectedQuestionCount: unit.selectedQuestionCount,
      })),
    });
    router.push(buildReplanAssessmentHref());
  }

  return (
    <div className="min-h-screen px-4 py-10" style={{ backgroundColor: "var(--bg-page)" }}>
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -right-40 -top-40 h-96 w-96 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-primary-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-2xl">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              Tối ưu lộ trình học
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Tạo phạm vi assessment từ phần bạn đã biết rồi chuyển sang trang assessment hiện có.
            </p>
          </div>
        </div>

        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {step === "describe" ? "Describe" : "Review"}
              </span>
              <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                {step === "describe" ? "· Knowledge claim" : "· Verification scope"}
              </span>
            </div>
            <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              {step === "describe" ? "1 / 3" : "3 / 3"}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div className={`h-full rounded-full bg-primary-600 transition-all duration-500 ease-out ${step === "describe" ? "w-1/3" : "w-full"}`} />
          </div>
        </div>

        <div className="card space-y-5">
          {step === "describe" ? (
            <ReplanKnowledgeClaimStep
              claim={claim}
              message={message}
              onClaimChange={setClaim}
              onContinue={continueToAnalysis}
            />
          ) : (
            <>
              {showPrerequisites ? (
                <PrerequisiteSuggestionDialog
                  targetTitle="Faster R-CNN"
                  suggestions={demoPrerequisites}
                  onInclude={includePrerequisites}
                  onSkip={() => setShowPrerequisites(false)}
                />
              ) : null}
              {message && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
                  {message}
                </div>
              )}
              {reviewUnits.length > 0 ? (
                <ReplanScopeReviewStep
                  units={reviewUnits}
                  onDescribeAgain={describeAgain}
                  onStartAssessment={startAssessment}
                />
              ) : (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={describeAgain}
                    className="rounded-xl border-2 px-6 py-3 text-sm font-semibold transition-all duration-150 hover:shadow-sm active:scale-[0.99]"
                    style={{
                      borderColor: "var(--border)",
                      color: "var(--text-primary)",
                      backgroundColor: "var(--bg-card)",
                    }}
                  >
                    Describe again
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
