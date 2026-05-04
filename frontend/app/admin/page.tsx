"use client";

// app/admin/page.tsx — Phase 9: Overview KPI grid + charts.

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import KpiCard from "@/components/admin/KpiCard";
import ChartCard from "@/components/admin/ChartCard";
import {
  adminApi,
  AdminOverview,
  LlmStats,
  SignupPoint,
  SystemHealth,
} from "@/lib/admin-api";

function fmtUptime(seconds: number | null | undefined): string {
  if (!seconds && seconds !== 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h`;
}

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `${(p * 100).toFixed(2)}%`;
}

export default function AdminOverviewPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [system, setSystem] = useState<SystemHealth | null>(null);
  const [signups, setSignups] = useState<SignupPoint[]>([]);
  const [llm, setLlm] = useState<LlmStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [o, s, sg, l] = await Promise.all([
          adminApi.overview(),
          adminApi.systemHealth(),
          adminApi.signups(30),
          adminApi.llmStats(24),
        ]);
        if (cancelled) return;
        setOverview(o);
        setSystem(s);
        setSignups(sg);
        setLlm(l);
        setErr(null);
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
    <div className="space-y-6">
      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-cyan-600">
          Overview
        </p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white md:text-3xl">
          Realtime platform pulse
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Auto-refreshing every 30s · Postgres · Prometheus · LangFuse Cloud · Loki.
        </p>
        {err && (
          <p className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
            Failed to load some panels: {err}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
        <KpiCard
          label="Total users"
          value={overview?.total_users ?? "—"}
          loading={loading}
        />
        <KpiCard label="DAU" value={overview?.dau ?? "—"} hint="Last 24h" loading={loading} />
        <KpiCard label="MAU" value={overview?.mau ?? "—"} hint="Last 30d" loading={loading} />
        <KpiCard
          label="Signups (7d)"
          value={overview?.signups_7d ?? "—"}
          loading={loading}
        />
        <KpiCard
          label="LLM calls (24h)"
          value={overview?.llm_calls_24h ?? "—"}
          loading={loading}
        />
        <KpiCard
          label="Avg p95 latency"
          value={
            overview?.avg_latency_ms !== null && overview?.avg_latency_ms !== undefined
              ? `${overview.avg_latency_ms} ms`
              : "—"
          }
          hint="Prometheus"
          loading={loading}
        />
        <KpiCard
          label="Error rate"
          value={fmtPct(overview?.error_rate)}
          hint="5xx / total (5m)"
          loading={loading}
        />
        <KpiCard
          label="System uptime"
          value={fmtUptime(system?.uptime_seconds)}
          hint={`${system?.services.filter((x) => x.status === "healthy").length ?? 0}/${system?.services.length ?? 0} healthy`}
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <ChartCard title="Signups (last 30 days)" subtitle="users.created_at">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={signups} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="signupsFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => String(v).slice(5)}
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
                width={32}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  background: "rgba(255,255,255,0.95)",
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#0891b2"
                strokeWidth={2}
                fill="url(#signupsFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="LLM calls per hour (last 24h)" subtitle="qa_history.jsonl">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={llm?.calls_per_hour ?? []}
              margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="hour"
                tickFormatter={(v) => String(v).slice(11, 16)}
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
                width={32}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  background: "rgba(255,255,255,0.95)",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" fill="#4f46e5" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
