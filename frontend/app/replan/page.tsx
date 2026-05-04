"use client";

import { useState } from "react";
import { Brain, Loader2, AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

import ReplanKnowledgeClaimStep from "@/components/replan/ReplanKnowledgeClaimStep";
import PrerequisiteSuggestionDialog, { type PrerequisiteSuggestion } from "@/components/replan/PrerequisiteSuggestionDialog";
import ReplanScopeReviewStep, {
  type ReplanReviewUnit,
  type ReplanSelectedAssessmentUnit,
} from "@/components/replan/ReplanScopeReviewStep";
import { writeReplanAssessmentContext } from "@/lib/replan-assessment-context";
import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";
import { replanApi, type ReplanAnalyzeResponse } from "@/lib/replan-api";
import { writePendingCanonicalAssessment } from "@/lib/canonical-assessment-session";

export default function ReplanPage() {
  const router = useRouter();
  const [claim, setClaim] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [step, setStep] = useState<"describe" | "review">("describe");
  const [reviewUnits, setReviewUnits] = useState<ReplanReviewUnit[]>([]);
  const [showPrerequisites, setShowPrerequisites] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // Store backend prerequisites for the dialog
  const [backendPrerequisites, setBackendPrerequisites] = useState<
    (PrerequisiteSuggestion & { reviewUnit: ReplanReviewUnit })[]
  >([]);
  // Store the first matched unit title for the prerequisite dialog
  const [targetTitle, setTargetTitle] = useState("");

  async function continueToAnalysis() {
    const validation = validateReplanKnowledgeClaim(claim);
    if (!validation.ok) {
      setMessage(validation.message);
      return;
    }

    setMessage(validation.warning ?? null);
    setAnalyzeError(null);
    setIsAnalyzing(true);

    try {
      const response: ReplanAnalyzeResponse = await replanApi.analyze(claim);

      // Check guardrail flags
      if (response.guardrailFlags.includes("no_active_path")) {
        setMessage("Bạn chưa có lộ trình học. Hãy chọn khoá học và tạo lộ trình trước khi tối ưu.");
        setReviewUnits([]);
        setShowPrerequisites(false);
        setStep("review");
        setIsAnalyzing(false);
        return;
      }

      // Map backend response to component types
      const mappedUnits: ReplanReviewUnit[] = response.units.map((u) => ({
        canonicalUnitId: u.canonicalUnitId,
        title: u.title,
        source: u.source,
        suggestedForTitle: u.suggestedForTitle ?? undefined,
        knowledgePoints: u.knowledgePoints,
        questionCounts: u.questionCounts,
      }));

      // Map prerequisites with their review units
      const mappedPrereqs: (PrerequisiteSuggestion & { reviewUnit: ReplanReviewUnit })[] = response.prerequisites.map((p) => ({
        canonicalUnitId: p.canonicalUnitId,
        title: p.title,
        reason: p.reason,
        depth: p.depth,
        reviewUnit: {
          canonicalUnitId: p.reviewUnit.canonicalUnitId,
          title: p.reviewUnit.title,
          source: p.reviewUnit.source as "matched_from_description" | "suggested_prerequisite",
          suggestedForTitle: p.reviewUnit.suggestedForTitle ?? undefined,
          knowledgePoints: p.reviewUnit.knowledgePoints,
          questionCounts: p.reviewUnit.questionCounts,
        },
      }));

      setReviewUnits(mappedUnits);
      setBackendPrerequisites(mappedPrereqs);
      setTargetTitle(mappedUnits[0]?.title ?? "selected unit");
      setShowPrerequisites(mappedPrereqs.length > 0);

      if (mappedUnits.length === 0) {
        setMessage("Không tìm thấy unit nào trong lộ trình khớp với mô tả. Hãy thử mô tả cụ thể hơn.");
      }

      setStep("review");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Lỗi khi phân tích. Vui lòng thử lại.";
      setAnalyzeError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }

  function describeAgain() {
    setStep("describe");
    setShowPrerequisites(false);
    setAnalyzeError(null);
  }

  function includePrerequisites(suggestions: PrerequisiteSuggestion[]) {
    const suggestionIds = new Set(suggestions.map((s) => s.canonicalUnitId));
    setReviewUnits([
      ...reviewUnits,
      ...backendPrerequisites
        .filter((p) => suggestionIds.has(p.canonicalUnitId))
        .map((p) => p.reviewUnit),
    ]);
    setShowPrerequisites(false);
  }

  async function startAssessment(selectedUnits: ReplanSelectedAssessmentUnit[]) {
    setIsStarting(true);
    setAnalyzeError(null);

    try {
      // Call backend to start assessment with exact unit + difficulty filters
      const response = await replanApi.startAssessment(
        selectedUnits.map((u) => ({
          canonicalUnitId: u.canonicalUnitId,
          difficultyFilter: u.difficultyFilter,
        })),
      );

      // Write canonical assessment context for the /assessment page
      writePendingCanonicalAssessment({
        canonicalUnitIds: response.canonicalUnitIds,
        unitNameMap: response.unitNameMap,
        assessmentDepth: "deep",
      });

      // Also write replan-specific scope metadata
      writeReplanAssessmentContext({
        units: selectedUnits.map((u) => ({
          canonicalUnitId: u.canonicalUnitId,
          title: u.title,
          difficultyFilter: u.difficultyFilter,
          selectedQuestionCount: u.selectedQuestionCount,
        })),
      });

      // Navigate to the assessment page
      router.push(response.assessmentHref);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Lỗi khi tạo bài assessment. Vui lòng thử lại.";
      setAnalyzeError(errorMessage);
      setIsStarting(false);
    }
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
            <>
              <ReplanKnowledgeClaimStep
                claim={claim}
                message={message}
                onClaimChange={setClaim}
                onContinue={continueToAnalysis}
              />
              {isAnalyzing && (
                <div className="flex items-center justify-center gap-2 py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                  <span className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                    Đang phân tích lộ trình của bạn...
                  </span>
                </div>
              )}
              {analyzeError && (
                <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{analyzeError}</span>
                </div>
              )}
            </>
          ) : (
            <>
              {showPrerequisites ? (
                <PrerequisiteSuggestionDialog
                  targetTitle={targetTitle}
                  suggestions={backendPrerequisites}
                  onInclude={includePrerequisites}
                  onSkip={() => setShowPrerequisites(false)}
                />
              ) : null}
              {message && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
                  {message}
                </div>
              )}
              {analyzeError && (
                <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{analyzeError}</span>
                </div>
              )}
              {isStarting && (
                <div className="flex items-center justify-center gap-2 py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                  <span className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                    Đang tạo bài assessment...
                  </span>
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
