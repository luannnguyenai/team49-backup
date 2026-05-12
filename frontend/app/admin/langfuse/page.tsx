"use client";

const LANGFUSE_HOST = process.env.NEXT_PUBLIC_LANGFUSE_HOST || "";

export default function AdminLangfusePage() {
  const hasHost = LANGFUSE_HOST.trim().length > 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="rounded-[24px] border border-slate-200/70 bg-white/70 px-5 py-4 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-600">
          LLM Observability
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-2xl">
          Langfuse
        </h2>
        <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-300">
          Trace LLM calls, prompts, latency, token usage và cost.
        </p>
      </div>

      {!hasHost ? (
        <div className="rounded-[24px] border border-amber-300/70 bg-amber-50/80 p-6 text-sm text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200">
          <p className="font-semibold">NEXT_PUBLIC_LANGFUSE_HOST chưa cấu hình.</p>
          <p className="mt-1">
            Set <code className="rounded bg-amber-100 px-1 dark:bg-amber-900/60">NEXT_PUBLIC_LANGFUSE_HOST</code> trong{" "}
            <code className="rounded bg-amber-100 px-1 dark:bg-amber-900/60">.env</code> để mở Langfuse từ admin dashboard.
          </p>
        </div>
      ) : (
        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                Live trace explorer
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Langfuse Cloud opens in a new tab for full traces, costs, and prompt history.
              </p>
            </div>
            <a
              href={LANGFUSE_HOST}
              target="_blank"
              rel="noreferrer"
              className="btn-primary px-4 py-2 text-xs"
            >
              Open in new tab →
            </a>
          </div>
          <div className="rounded-[18px] border border-slate-200/80 bg-slate-50/90 p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
            Langfuse Cloud sends security headers that block third-party iframe embedding (`X-Frame-Options: SAMEORIGIN` and `frame-ancestors &apos;none&apos;`). Use the button above to open the hosted UI directly.
          </div>
        </div>
      )}
    </div>
  );
}
