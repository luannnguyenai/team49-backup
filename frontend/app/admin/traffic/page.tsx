"use client";

// app/admin/traffic/page.tsx — Phase 12

import { useEffect, useState } from "react";

import KpiCard from "@/components/admin/KpiCard";
import { adminApi, TrafficSummary } from "@/lib/admin-api";

const GRAFANA_HOST = process.env.NEXT_PUBLIC_GRAFANA_HOST || "http://localhost:3001";
const TRAFFIC_DASHBOARD_UID = "a20-api-traffic";

function fmtSec(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  if (s < 1) return `${(s * 1000).toFixed(0)} ms`;
  return `${s.toFixed(2)} s`;
}

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `${(p * 100).toFixed(2)}%`;
}

export default function AdminTrafficPage() {
  const [summary, setSummary] = useState<TrafficSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await adminApi.trafficSummary();
        if (!cancelled) {
          setSummary(r);
          setErr(null);
        }
      } catch (e) {
        if (!cancelled) setErr(String((e as Error).message ?? e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 15_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6">
        <KpiCard
          label="Req / sec (1m)"
          value={summary?.rps_1m != null ? summary.rps_1m.toFixed(2) : "—"}
          loading={loading}
        />
        <KpiCard label="p50 latency" value={fmtSec(summary?.latency_seconds.p50)} loading={loading} />
        <KpiCard label="p95 latency" value={fmtSec(summary?.latency_seconds.p95)} loading={loading} />
        <KpiCard label="p99 latency" value={fmtSec(summary?.latency_seconds.p99)} loading={loading} />
        <KpiCard label="4xx rate" value={fmtPct(summary?.rate_4xx)} loading={loading} />
        <KpiCard label="5xx rate" value={fmtPct(summary?.rate_5xx)} loading={loading} />
      </div>

      {err && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
      )}

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Grafana — API Traffic</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Embedded from <code>{GRAFANA_HOST}</code> · provisioned dashboard <code>{TRAFFIC_DASHBOARD_UID}</code>.
            </p>
          </div>
          <a
            href={`${GRAFANA_HOST}/d/${TRAFFIC_DASHBOARD_UID}`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Open Grafana →
          </a>
        </div>
        <div className="overflow-hidden rounded-[20px] border border-slate-200/80 bg-white/80">
          <iframe
            src={`${GRAFANA_HOST}/d/${TRAFFIC_DASHBOARD_UID}?theme=light&kiosk`}
            title="Grafana — API Traffic"
            className="h-[720px] w-full"
            loading="lazy"
          />
        </div>
      </div>
    </div>
  );
}
