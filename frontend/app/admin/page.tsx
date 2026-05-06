"use client";

// app/admin/page.tsx — Phase 9: Overview KPI grid + charts.

import { useEffect, useState } from "react";

import KpiCard from "@/components/admin/KpiCard";
import KpiGroup from "@/components/admin/KpiGroup";
import {
  adminApi,
  AdminOverview,
  CurrentModel,
} from "@/lib/admin-api";
import { overviewTooltips } from "@/lib/admin-tooltips";

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `${(p * 100).toFixed(2)}%`;
}

export default function AdminOverviewPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [model, setModel] = useState<CurrentModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [o, m] = await Promise.all([
          adminApi.overview(),
          adminApi.currentModel().catch(() => null),
        ]);
        if (cancelled) return;
        setOverview(o);
        setModel(m);
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

      <KpiGroup title="Người dùng" cols={5}>
        <KpiCard
          label="Total users"
          value={overview?.total_users ?? "—"}
          tooltip={overviewTooltips.totalUsers}
          loading={loading}
        />
        <KpiCard
          label="DAU"
          value={overview?.dau ?? "—"}
          hint="Last 24h"
          tooltip={overviewTooltips.dau}
          loading={loading}
        />
        <KpiCard
          label="MAU"
          value={overview?.mau ?? "—"}
          hint="Last 30d"
          tooltip={overviewTooltips.mau}
          loading={loading}
        />
        <KpiCard
          label="Signups (7d)"
          value={overview?.signups_7d ?? "—"}
          tooltip={overviewTooltips.signups7d}
          loading={loading}
        />
        <KpiCard
          label="Online now"
          value={overview?.active_now ?? "—"}
          hint="Active ≤ 15m"
          tooltip={overviewTooltips.activeNow}
          loading={loading}
        />
      </KpiGroup>

      <KpiGroup title="AI Service" cols={4}>
        <KpiCard
          label="LLM calls (24h)"
          value={overview?.llm_calls_24h ?? "—"}
          tooltip={overviewTooltips.llmCalls24h}
          loading={loading}
        />
        <KpiCard
          label="Model đang dùng"
          value={
            model ? (
              <span title={`${model.provider}/${model.name}`} className="block truncate">
                {model.name}
              </span>
            ) : (
              "—"
            )
          }
          hint={model ? `${model.provider} · fast: ${model.fast_model}` : "Loading…"}
          tooltip={overviewTooltips.modelCurrent}
          loading={loading}
        />
        <KpiCard
          label="Error rate"
          value={fmtPct(overview?.error_rate)}
          hint="5xx / total (5m)"
          tooltip={overviewTooltips.errorRate}
          loading={loading}
        />
      </KpiGroup>
    </div>
  );
}
