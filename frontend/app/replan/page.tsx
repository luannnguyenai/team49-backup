"use client";

import { Suspense, useState } from "react";
import { ArrowLeft, Brain, Loader2, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

import ReplanKnowledgeClaimStep from "@/components/replan/ReplanKnowledgeClaimStep";
import PrerequisiteSuggestionDialog, { type PrerequisiteSuggestion } from "@/components/replan/PrerequisiteSuggestionDialog";
import ReplanScopeReviewStep, {
  type ReplanReviewUnit,
  type ReplanSelectedAssessmentUnit,
} from "@/components/replan/ReplanScopeReviewStep";
import ErrorModal from "@/components/replan/ErrorModal";
import { writeReplanAssessmentContext } from "@/lib/replan-assessment-context";
import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";
import { replanApi, type ReplanAnalyzeResponse } from "@/lib/replan-api";
import {
  writePendingCanonicalAssessment,
  writeStartedCanonicalAssessment,
} from "@/lib/canonical-assessment-session";

function isSafeInternalPath(value: string | null): value is string {
  return Boolean(value && value.startsWith("/") && !value.startsWith("//"));
}

function ReplanPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [claim, setClaim] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [step, setStep] = useState<"describe" | "review">("describe");
  const [reviewUnits, setReviewUnits] = useState<ReplanReviewUnit[]>([]);
  const [showPrerequisites, setShowPrerequisites] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [statusPopup, setStatusPopup] = useState<{
    title: string;
    message: string;
  } | null>(null);

  // Store backend prerequisites for the dialog
  const [backendPrerequisites, setBackendPrerequisites] = useState<
    (PrerequisiteSuggestion & { reviewUnit: ReplanReviewUnit })[]
  >([]);

  async function continueToAnalysis() {
    const validation = validateReplanKnowledgeClaim(claim);
    if (!validation.ok && validation.reason === "too_short") {
      setMessage(validation.message);
      return;
    }

    setMessage(validation.ok ? validation.warning ?? null : null);
    setAnalyzeError(null);
    setIsAnalyzing(true);

    try {
      const response: ReplanAnalyzeResponse = await replanApi.analyze(claim);

      // Check guardrail flags
      if (response.status !== "ready" && response.popup) {
        setStatusPopup({
          title: response.popup.title,
          message: response.popup.message,
        });
      }

      if (response.status === "no_active_path" || response.guardrailFlags.includes("no_active_path")) {
        setMessage(response.popup?.message ?? "You don't have an active learning path yet. Please select a course and create a path before optimizing.");
        setReviewUnits([]);
        setShowPrerequisites(false);
        setStep("review");
        setIsAnalyzing(false);
        return;
      }

      if (response.status === "all_already_mastered") {
        setMessage(null);
        setReviewUnits([]);
        setShowPrerequisites(false);
        setStep("review");
        setIsAnalyzing(false);
        return;
      }

      if (response.status === "guardrail_blocked") {
        setMessage(null);
        setReviewUnits([]);
        setShowPrerequisites(false);
        setStep("describe");
        setIsAnalyzing(false);
        return;
      }

      if (response.status === "no_matching_units" || response.guardrailFlags.includes("no_matching_units")) {
        setMessage(response.popup?.message ?? "No units in your learning path match your description. Your course may not cover these topics yet.");
        setReviewUnits([]);
        setShowPrerequisites(false);
        setStep("review");
        setIsAnalyzing(false);
        return;
      }

      if (response.status === "internal_error" || response.guardrailFlags.includes("internal_error")) {
        // Extract error details from guardrail flags (if available)
        const errorDetail = response.guardrailFlags.find((f) => f.includes(":"));
        const errorMessage = errorDetail
          ? `An error occurred: ${errorDetail}`
          : "An error occurred while analyzing. Please try again later.";
        setAnalyzeError(errorMessage);
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
      setShowPrerequisites(mappedPrereqs.length > 0);

      if (mappedUnits.length === 0) {
        setMessage("No units found in your path match the description. Try being more specific.");
      }

      setStep("review");
    } catch (err: unknown) {
      let errorMessage = "Error analyzing your claim. Please try again.";

      if (err instanceof Error) {
        // Network errors
        if (err.message.includes("fetch") || err.message.includes("network")) {
          errorMessage = "Cannot connect to server. Check your network connection and try again.";
        }
        // Timeout errors
        else if (err.message.includes("timeout") || err.message.includes("aborted")) {
          errorMessage = "Request timed out. Please try again.";
        }
        // 500 errors from backend
        else if (err.message.includes("500") || err.message.includes("503")) {
          errorMessage = "Server is experiencing issues. Please try again in a few minutes.";
        }
        // 401 unauthorized
        else if (err.message.includes("401")) {
          errorMessage = "Your session has expired. Please log in again.";
        }
        // Use error message if it's user-friendly
        else if (err.message.length < 100) {
          errorMessage = err.message;
        }
      }

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

  function backToSource() {
    const returnTo = searchParams.get("returnTo");
    if (isSafeInternalPath(returnTo)) {
      router.push(returnTo);
      return;
    }

    const from = searchParams.get("from");
    if (from === "/replan") {
      router.push("/dashboard");
      return;
    }

    router.back();
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
      writeStartedCanonicalAssessment({
        sessionId: response.sessionId,
        questions: response.questions,
        canonicalUnitIds: response.canonicalUnitIds,
        unitNameMap: response.unitNameMap,
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
      let errorMessage = "Error creating assessment. Please try again.";

      if (err instanceof Error) {
        if (err.message.includes("fetch") || err.message.includes("network")) {
          errorMessage = "Cannot connect to server. Check your network connection and try again.";
        } else if (err.message.includes("timeout") || err.message.includes("aborted")) {
          errorMessage = "Request timed out. Please try again.";
        } else if (err.message.includes("500") || err.message.includes("503")) {
          errorMessage = "Server is experiencing issues. Please try again in a few minutes.";
        } else if (err.message.includes("401")) {
          errorMessage = "Your session has expired. Please log in again.";
        } else if (err.message.length < 100) {
          errorMessage = err.message;
        }
      }

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
        {/* Back button */}
        <button
          type="button"
          onClick={backToSource}
          className="mb-4 flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary-600"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
              Optimize Learning Path
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Create an assessment scope from what you already know, then continue to the existing assessment page.
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
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
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
                    Analyzing your learning path...
                  </span>
                </div>
              )}
            </>
          ) : (
            <>
              {showPrerequisites ? (
                <PrerequisiteSuggestionDialog
                  suggestions={backendPrerequisites}
                  onInclude={includePrerequisites}
                  onSkip={() => setShowPrerequisites(false)}
                />
              ) : null}
              {message && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {message}
                </div>
              )}
              {isStarting && (
                <div className="flex items-center justify-center gap-2 py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                  <span className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                    Creating assessment...
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

      {/* Error Modal - popup for all errors */}
      {analyzeError && (
        <ErrorModal
          message={analyzeError}
          onDismiss={() => setAnalyzeError(null)}
        />
      )}
      {statusPopup && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setStatusPopup(null)}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label={statusPopup.title}
            className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-start gap-3">
              <div className="flex-1">
                <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                  {statusPopup.title}
                </h3>
                <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  {statusPopup.message}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setStatusPopup(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setStatusPopup(null)}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default function ReplanPage() {
  return (
    <Suspense fallback={null}>
      <ReplanPageContent />
    </Suspense>
  );
}
