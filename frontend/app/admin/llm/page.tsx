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
import ChartCard from "@/components/admin/ChartCard";
import { adminApi, AdminOverview, LlmStats } from "@/lib/admin-api";

const LANGFUSE_HOST = process.env.NEXT_PUBLIC_LANGFUSE_HOST || "https://cloud.langfuse.com";

export default function AdminLlmPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [stats, setStats] = useState<LlmStats | null>(null);
  const [recent, setRecent] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [o, s, r] = await Promise.all([
          adminApi.overview(),
          adminApi.llmStats(24),
          adminApi.llmRecent(10),
        ]);
        if (!cancelled) {
          setOverview(o);
          setStats(s);
          setRecent(r);
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
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard
          label="LLM calls (24h)"
          value={overview?.llm_calls_24h ?? "—"}
          loading={loading}
        />
        <KpiCard
          label="Avg p95 latency"
          value={overview?.avg_latency_ms != null ? `${overview.avg_latency_ms} ms` : "—"}
          loading={loading}
        />
        <KpiCard
          label="Total calls (window)"
          value={stats?.total_calls ?? "—"}
          hint={`${stats?.window_hours ?? 0}h window`}
          loading={loading}
        />
        <KpiCard
          label="Errors (window)"
          value={stats?.errors ?? "—"}
          hint="qa_history.jsonl"
          loading={loading}
        />
      </div>

      {err && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <ChartCard title="LLM calls per hour" subtitle="aggregated from qa_history.jsonl">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={stats?.calls_per_hour ?? []} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} tickFormatter={(v) => String(v).slice(11, 16)} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={32} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
              <Line type="monotone" dataKey="count" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top users (window)" subtitle="by call count">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={(stats?.top_users ?? []).map((t) => ({ ...t, label: t.user_id.slice(0, 8) }))}
              margin={{ left: 16, right: 8, top: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={70} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
              <Bar dataKey="count" fill="#0891b2" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">LangFuse</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Full traces, costs and prompt history available in LangFuse Cloud.
            </p>
          </div>
          <a
            href={LANGFUSE_HOST}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Open LangFuse →
          </a>
        </div>
        <div className="overflow-hidden rounded-[20px] border border-slate-200/80 bg-white/80">
          <iframe
            src={LANGFUSE_HOST}
            title="LangFuse"
            className="h-[480px] w-full"
            loading="lazy"
          />
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <h3 className="mb-3 text-base font-semibold text-slate-900 dark:text-white">Recent LLM events</h3>
        <pre className="max-h-80 overflow-auto rounded-xl bg-slate-950/95 p-4 text-xs text-slate-200">
{recent.map((r, i) => JSON.stringify(r)).join("\n")}
        </pre>
      </div>
    </div>
  );
}
