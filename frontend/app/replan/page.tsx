"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { useRouter } from "next/navigation";

import ReplanKnowledgeClaimStep from "@/components/replan/ReplanKnowledgeClaimStep";
import ReplanScopeReviewStep, { type ReplanReviewUnit } from "@/components/replan/ReplanScopeReviewStep";
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

export default function ReplanPage() {
  const router = useRouter();
  const [claim, setClaim] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [step, setStep] = useState<"describe" | "review">("describe");

  function continueToAnalysis() {
    const validation = validateReplanKnowledgeClaim(claim);
    if (!validation.ok) {
      setMessage(validation.message);
      return;
    }
    setMessage(validation.warning ?? null);
    setStep("review");
  }

  function describeAgain() {
    setStep("describe");
  }

  function startAssessment(selectedUnits: ReplanReviewUnit[]) {
    writeReplanAssessmentContext({
      units: selectedUnits.map((unit) => ({
        canonicalUnitId: unit.canonicalUnitId,
        title: unit.title,
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
              {message && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
                  {message}
                </div>
              )}
              <ReplanScopeReviewStep
                units={demoScopeUnits}
                onDescribeAgain={describeAgain}
                onStartAssessment={startAssessment}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
