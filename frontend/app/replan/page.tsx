"use client";

import { useState } from "react";
import { Brain } from "lucide-react";

import { validateReplanKnowledgeClaim } from "@/lib/replan-claim-guardrails";

export default function ReplanPage() {
  const [claim, setClaim] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  function continueToAnalysis() {
    const validation = validateReplanKnowledgeClaim(claim);
    if (!validation.ok) {
      setMessage(validation.message);
      return;
    }
    setMessage(validation.warning ?? null);
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
                Describe
              </span>
              <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                · Knowledge claim
              </span>
            </div>
            <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              1 / 3
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div className="h-full w-1/3 rounded-full bg-primary-600 transition-all duration-500 ease-out" />
          </div>
        </div>

        <div className="card space-y-5">
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              Bạn đã biết phần nào rồi?
            </p>
            <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Mô tả cụ thể những phần bạn đã nắm để hệ thống tạo bài kiểm tra xác nhận. Mô tả này không tự động bỏ qua bài học. Kết quả assessment mới được dùng để cập nhật lộ trình.
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
              Bạn đã biết phần nào rồi?
            </label>
            <textarea
              id="replan-knowledge-claim"
              aria-label="Bạn đã biết phần nào rồi?"
              value={claim}
              onChange={(event) => setClaim(event.target.value)}
              className="mt-3 min-h-28 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
              style={{
                borderColor: "var(--border)",
                backgroundColor: "var(--bg-card)",
                color: "var(--text-primary)",
              }}
              placeholder={"Ví dụ:\n- Tôi đã nắm CNN, convolution, pooling.\n- Tôi biết Faster R-CNN nhưng chưa chắc YOLO.\n- Tôi hiểu object detection cơ bản, muốn kiểm tra để bỏ bớt phần nền tảng."}
            />
          </div>

          <div className="flex items-center justify-end pt-2">
            <button
              type="button"
              onClick={continueToAnalysis}
              className="rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
