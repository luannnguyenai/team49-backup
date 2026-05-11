"use client";

// app/admin/llm/page.tsx — Phase 11

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import KpiCard from "@/components/admin/KpiCard";
import KpiGroup from "@/components/admin/KpiGroup";
import ChartCard from "@/components/admin/ChartCard";
import {
  adminApi,
  type FeedbackStats,
  type LlmStats,
  type ModelHealthRow,
  type NegativeFeedbackRow,
} from "@/lib/admin-api";
import { llmTooltips } from "@/lib/admin-tooltips";
import { CHART_GRID, CHART_PALETTE, CHART_STATUS } from "@/lib/admin/chart-theme";

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `${(p * 100).toFixed(1)}%`;
}

function fmtMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value)} ms`;
}

export default function AdminLlmPage() {
  const [stats, setStats] = useState<LlmStats | null>(null);
  const [recent, setRecent] = useState<Record<string, unknown>[]>([]);
  const [modelHealth, setModelHealth] = useState<ModelHealthRow[]>([]);
  const [feedback, setFeedback] = useState<FeedbackStats | null>(null);
  const [negatives, setNegatives] = useState<NegativeFeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [s, r, mh, fb, neg] = await Promise.all([
          adminApi.llmStats(24),
          adminApi.llmRecent(10),
          adminApi.modelHealth().catch(() => ({ models: [] })),
          adminApi.feedbackStats(14),
          adminApi.feedbackNegative(20),
        ]);
        if (!cancelled) {
          setStats(s);
          setRecent(r);
          setModelHealth(mh.models);
          setFeedback(fb);
          setNegatives(neg);
          setErr(null);
        }
      } catch (e) {
        if (!cancelled) setErr(String((e as Error).message ?? e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="rounded-[24px] border border-slate-200/70 bg-white/70 px-5 py-4 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-600">
          LLM Monitoring
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-2xl">
          Tutor latency, feedback, and call volume
        </h2>
        <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-300">
          Focused on first-status latency, answer latency, user feedback, and recent tutor activity.
        </p>
      </div>

      <section className="space-y-3">
        <header className="flex items-baseline justify-between gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            Model health
          </h3>
        </header>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {modelHealth.length > 0 ? (
            modelHealth.map((item) => {
              const statusClass =
                item.status === "healthy"
                  ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                  : item.status === "degraded"
                    ? "bg-amber-500/10 text-amber-700 dark:text-amber-300"
                    : "bg-rose-500/10 text-rose-700 dark:text-rose-300";
              return (
                <div
                  key={item.id}
                  className="rounded-[18px] border border-slate-200/70 bg-white/70 p-4 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">{item.label}</p>
                      <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                        {item.provider}/{item.model}
                      </p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusClass}`}>
                      {item.status}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <span>{fmtMs(item.latency_ms)}</span>
                    {item.base_url ? <span className="truncate">{item.base_url}</span> : null}
                  </div>
                  {item.error ? (
                    <p className="mt-2 line-clamp-2 text-xs text-rose-600 dark:text-rose-300">{item.error}</p>
                  ) : null}
                </div>
              );
            })
          ) : (
            <div className="rounded-[18px] border border-slate-200/70 bg-white/70 p-4 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
              {loading ? "Checking models..." : "No model health data."}
            </div>
          )}
        </div>
      </section>

      <KpiGroup title="Volume" cols={2}>
        <KpiCard
          label="LLM calls (window)"
          value={stats?.total_calls ?? "—"}
          hint={`${stats?.window_hours ?? 0}h window`}
          tooltip={llmTooltips.callsWindow}
          loading={loading}
        />
        <KpiCard
          label="Errors (window)"
          value={stats?.errors ?? "—"}
          hint="qa_history.jsonl"
          tooltip={llmTooltips.errorsWindow}
          loading={loading}
        />
      </KpiGroup>

      <KpiGroup title="Latency" cols={4}>
        <KpiCard
          label="First status p95"
          value={fmtMs(stats?.tutor_latency_per_hour.at(-1)?.first_status_p95_ms)}
          hint="Latest hourly bucket"
          tooltip={llmTooltips.firstStatusP95}
          loading={loading}
        />
        <KpiCard
          label="First status p50"
          value={fmtMs(stats?.tutor_latency_per_hour.at(-1)?.first_status_p50_ms)}
          hint="Latest hourly bucket"
          tooltip={llmTooltips.firstStatusP50}
          loading={loading}
        />
        <KpiCard
          label="First answer p95"
          value={fmtMs(stats?.tutor_latency_per_hour.at(-1)?.first_answer_p95_ms)}
          hint="Latest hourly bucket"
          tooltip={llmTooltips.firstAnswerP95}
          loading={loading}
        />
        <KpiCard
          label="First answer p50"
          value={fmtMs(stats?.tutor_latency_per_hour.at(-1)?.first_answer_p50_ms)}
          hint="Latest hourly bucket"
          tooltip={llmTooltips.firstAnswerP50}
          loading={loading}
        />
      </KpiGroup>

      <KpiGroup title="Feedback (14d)" cols={4}>
        <KpiCard
          label="Positive ratings"
          value={feedback?.positive ?? "—"}
          hint="👍"
          tooltip={llmTooltips.positiveRatings}
          loading={loading}
        />
        <KpiCard
          label="Negative ratings"
          value={feedback?.negative ?? "—"}
          hint="👎"
          tooltip={llmTooltips.negativeRatings}
          loading={loading}
        />
        <KpiCard
          label="Positive ratio"
          value={fmtPct(feedback?.positive_ratio)}
          hint={`Total rated: ${feedback?.total_ratings ?? 0}`}
          tooltip={llmTooltips.positiveRatio}
          loading={loading}
        />
        <KpiCard
          label="Unrated (24h)"
          value={feedback?.unrated_24h ?? "—"}
          hint="LLM calls without thumb"
          tooltip={llmTooltips.unrated24h}
          loading={loading}
        />
      </KpiGroup>

      {err && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
      )}

      <ChartCard
        title="Feedback trend (14 days)"
        subtitle="qa_history.rating · 👍 emerald / 👎 rose"
        height={220}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={feedback?.trend ?? []}
            margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
            stackOffset="sign"
          >
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID.stroke} vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => String(v).slice(5)}
            />
            <YAxis
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
              width={32}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{ borderRadius: 12, border: `1px solid ${CHART_GRID.tooltipBorder}`, fontSize: 12 }}
            />
            <Bar dataKey="positive" stackId="ratings" fill={CHART_STATUS.success} radius={[6, 6, 0, 0]} />
            <Bar dataKey="negative" stackId="ratings" fill={CHART_STATUS.error} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <ChartCard title="LLM calls per hour" subtitle="aggregated from qa_history.jsonl" height={240}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={stats?.calls_per_hour ?? []} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID.stroke} vertical={false} />
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: CHART_GRID.tick }} tickLine={false} axisLine={false} tickFormatter={(v) => String(v).slice(11, 16)} />
              <YAxis tick={{ fontSize: 11, fill: CHART_GRID.tick }} tickLine={false} axisLine={false} width={32} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: `1px solid ${CHART_GRID.tooltipBorder}`, fontSize: 12 }} />
              <Line type="monotone" dataKey="count" stroke={CHART_PALETTE.primary} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top users (window)" subtitle="by call count" height={240}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={(stats?.top_users ?? []).map((t) => ({ ...t, label: t.user_id.slice(0, 8) }))}
              margin={{ left: 16, right: 8, top: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID.stroke} horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: CHART_GRID.tick }} tickLine={false} axisLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: CHART_GRID.tick }} tickLine={false} axisLine={false} width={70} />
              <Tooltip contentStyle={{ borderRadius: 12, border: `1px solid ${CHART_GRID.tooltipBorder}`, fontSize: 12 }} />
              <Bar dataKey="count" fill={CHART_PALETTE.primary} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard
        title="Tutor streaming latency"
        subtitle="Prometheus histogram quantiles · solid = p95 · dashed = p50"
        height={260}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={stats?.tutor_latency_per_hour ?? []}
            margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID.stroke} vertical={false} />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => String(v).slice(11, 16)}
            />
            <YAxis
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
              width={48}
              tickFormatter={(v) => `${Math.round(Number(v))}`}
            />
            <Tooltip
              formatter={(value) =>
                fmtMs(
                  typeof value === "number"
                    ? value
                    : value == null
                      ? null
                      : Number(value),
                )
              }
              labelFormatter={(value) => `Hour ${String(value).slice(11, 16)}`}
              contentStyle={{ borderRadius: 12, border: `1px solid ${CHART_GRID.tooltipBorder}`, fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="first_status_p95_ms"
              name="First status p95"
              stroke={CHART_PALETTE.primary}
              strokeWidth={2.5}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="first_answer_p95_ms"
              name="First answer p95"
              stroke={CHART_PALETTE.secondary}
              strokeWidth={2.5}
              dot={{ r: 2 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="first_status_p50_ms"
              name="First status p50"
              stroke={CHART_PALETTE.tertiary}
              strokeWidth={1.75}
              strokeDasharray="6 4"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="first_answer_p50_ms"
              name="First answer p50"
              stroke={CHART_PALETTE.quinary}
              strokeWidth={1.75}
              strokeDasharray="6 4"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="space-y-5">
        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                Recent negative feedback
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Last {negatives.length} answers rated 👎.
              </p>
            </div>
          </div>
          {negatives.length === 0 ? (
            <p className="rounded-xl bg-emerald-500/10 px-4 py-3 text-xs text-emerald-700 dark:text-emerald-300">
              No negative ratings yet.
            </p>
          ) : (
            <div className="divide-y divide-slate-200/70 dark:divide-slate-800">
              {negatives.map((n) => (
                <div key={n.id} className="py-3">
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <span>
                      #{n.id} · lecture <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">{n.lecture_id?.slice(0, 14) ?? "—"}</code>
                    </span>
                    <span>{n.created_at ? new Date(n.created_at).toLocaleString() : "—"}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">
                    Q: {n.question}
                  </p>
                  <p className="mt-1 line-clamp-3 text-sm text-slate-600 dark:text-slate-300">
                    A: {n.answer}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
          <h3 className="mb-3 text-base font-semibold text-slate-900 dark:text-white">Recent LLM events</h3>
          <pre className="max-h-72 overflow-auto rounded-xl bg-slate-950/95 p-4 text-xs text-slate-200">
{recent.map((r) => JSON.stringify(r)).join("\n")}
          </pre>
        </div>
      </div>
    </div>
  );
}
