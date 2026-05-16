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

function fmtCheckedAt(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function modelStatusClass(status: string): string {
  if (status === "healthy") {
    return "bg-emerald-500/10 text-emerald-700";
  }
  if (status === "degraded") {
    return "bg-amber-500/10 text-amber-700";
  }
  return "bg-rose-500/10 text-rose-700";
}

export default function AdminLlmPage() {
  const [stats, setStats] = useState<LlmStats | null>(null);
  const [recent, setRecent] = useState<Record<string, unknown>[]>([]);
  const [modelHealth, setModelHealth] = useState<ModelHealthRow[]>([]);
  const [modelHealthError, setModelHealthError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<FeedbackStats | null>(null);
  const [negatives, setNegatives] = useState<NegativeFeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [s, r, mhResult, fb, neg] = await Promise.all([
          adminApi.llmStats(24),
          adminApi.llmRecent(10),
          adminApi
            .modelHealth()
            .then((data) => ({ data, error: null as string | null }))
            .catch((error) => ({
              data: { models: [] },
              error: String((error as Error).message ?? error),
            })),
          adminApi.feedbackStats(14),
          adminApi.feedbackNegative(20),
        ]);
        if (!cancelled) {
          setStats(s);
          setRecent(r);
          setModelHealth(mhResult.data.models);
          setModelHealthError(mhResult.error);
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
      <div className="rounded-[24px] border border-slate-200/70 bg-white/70 px-5 py-4 backdrop-blur-md">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-600">
          LLM Monitoring
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900 md:text-2xl">
          Tutor latency, feedback, and call volume
        </h2>
        <p className="mt-1.5 text-sm text-slate-600">
          Focused on first-status latency, answer latency, user feedback, and recent tutor activity.
        </p>
      </div>

      <section className="space-y-3">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Model health
            </h3>
            <p className="mt-1 text-base font-semibold text-slate-900">
              Configured models
            </p>
          </div>
          <span className="text-xs text-slate-500">
            {modelHealth.length} model{modelHealth.length === 1 ? "" : "s"}
          </span>
        </header>
        <div className="overflow-hidden rounded-[18px] border border-slate-200/70 bg-white/70 backdrop-blur-md">
          {modelHealthError ? (
            <div className="border-b border-amber-200/70 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              <p className="font-semibold">Model health unavailable</p>
              <p className="mt-1 text-xs">{modelHealthError}</p>
            </div>
          ) : null}

          {modelHealth.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200/70 text-sm">
                <thead className="bg-slate-50/80 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Model</th>
                    <th className="px-4 py-3">Provider</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Latency</th>
                    <th className="px-4 py-3">Base URL</th>
                    <th className="px-4 py-3">Last checked</th>
                    <th className="px-4 py-3">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {modelHealth.map((item) => (
                    <tr key={item.id} className="align-top">
                      <td className="px-4 py-3">
                        <p className="font-semibold text-slate-900">{item.label}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.model}</p>
                        {item.is_default ? (
                          <span className="mt-2 inline-flex rounded-full bg-cyan-500/10 px-2 py-0.5 text-[11px] font-semibold text-cyan-700">
                            default
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{item.provider}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${modelStatusClass(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{fmtMs(item.latency_ms)}</td>
                      <td className="max-w-[260px] px-4 py-3 text-xs text-slate-500">
                        <span className="break-all">{item.base_url ?? "default provider endpoint"}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{fmtCheckedAt(item.checked_at)}</td>
                      <td className="max-w-[300px] px-4 py-3 text-xs text-rose-600">
                        <span className="line-clamp-3">{item.error ?? "—"}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-sm text-slate-500">
              {loading ? "Checking configured models..." : "No configured model health data returned."}
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
        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Recent negative feedback
              </h3>
              <p className="text-xs text-slate-500">
                Last {negatives.length} answers rated 👎.
              </p>
            </div>
          </div>
          {negatives.length === 0 ? (
            <p className="rounded-xl bg-emerald-500/10 px-4 py-3 text-xs text-emerald-700">
              No negative ratings yet.
            </p>
          ) : (
            <div className="divide-y divide-slate-200/70">
              {negatives.map((n) => (
                <div key={n.id} className="py-3">
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                    <span>
                      #{n.id} · lecture <code className="rounded bg-slate-100 px-1">{n.lecture_id?.slice(0, 14) ?? "—"}</code>
                    </span>
                    <span>{n.created_at ? new Date(n.created_at).toLocaleString() : "—"}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    Q: {n.question}
                  </p>
                  <p className="mt-1 line-clamp-3 text-sm text-slate-600">
                    A: {n.answer}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md">
          <h3 className="mb-3 text-base font-semibold text-slate-900">Recent LLM events</h3>
          <pre className="max-h-72 overflow-auto rounded-xl bg-slate-950/95 p-4 text-xs text-slate-200">
{recent.map((r) => JSON.stringify(r)).join("\n")}
          </pre>
        </div>
      </div>
    </div>
  );
}
