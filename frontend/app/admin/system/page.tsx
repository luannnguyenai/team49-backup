"use client";

// app/admin/system/page.tsx — Phase 13

import { useEffect, useRef, useState } from "react";
import {
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
import StatusBadge from "@/components/admin/StatusBadge";
import { adminApi, SystemHealth } from "@/lib/admin-api";
import { CHART_GRID, CHART_PALETTE } from "@/lib/admin/chart-theme";

type SeriesPoint = { t: number; cpu: number | null; ram: number | null };

const GRAFANA_HOST = process.env.NEXT_PUBLIC_GRAFANA_HOST || "http://localhost:3001";

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `${p.toFixed(1)}%`;
}

function fmtUptime(seconds: number | null | undefined): string {
  if (!seconds && seconds !== 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ${m % 60}m`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

export default function AdminSystemPage() {
  const [data, setData] = useState<SystemHealth | null>(null);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const startRef = useRef<number>(Date.now());

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await adminApi.systemHealth();
        if (cancelled) return;
        setData(r);
        setErr(null);
        const elapsed = Math.round((Date.now() - startRef.current) / 1000);
        setSeries((prev) => {
          const next = [...prev, { t: elapsed, cpu: r.cpu_pct, ram: r.ram_pct }];
          return next.slice(-60); // last ~10 minutes at 10s
        });
      } catch (e) {
        if (!cancelled) setErr(String((e as Error).message ?? e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 10_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="space-y-6">
      <KpiGroup title="Tài nguyên" cols={3}>
        <KpiCard label="CPU usage" value={fmtPct(data?.cpu_pct)} loading={loading} />
        <KpiCard label="RAM usage" value={fmtPct(data?.ram_pct)} loading={loading} />
        <KpiCard label="Disk usage" value={fmtPct(data?.disk_pct)} loading={loading} />
      </KpiGroup>

      <KpiGroup title="Hạ tầng" cols={2}>
        <KpiCard
          label="DB connections"
          value={data?.db_connections ?? "—"}
          hint="pg_stat_activity"
          loading={loading}
        />
        <KpiCard
          label="Redis hit rate"
          value={data?.redis_hit_rate != null ? `${(data.redis_hit_rate * 100).toFixed(1)}%` : "—"}
          hint="keyspace_hits / total"
          loading={loading}
        />
      </KpiGroup>

      <KpiGroup title="Trạng thái" cols={2}>
        <KpiCard
          label="Service uptime"
          value={fmtUptime(data?.uptime_seconds)}
          loading={loading}
        />
      </KpiGroup>

      {err && (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
      )}

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <h3 className="mb-3 text-base font-semibold text-slate-900 dark:text-white">Services</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {(data?.services ?? []).map((s) => (
            <div
              key={s.name}
              className="flex items-center justify-between rounded-xl border border-slate-200/70 bg-white/60 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/60"
            >
              <div>
                <p className="text-sm font-semibold capitalize text-slate-900 dark:text-white">
                  {s.name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">backend/postgres/redis</p>
              </div>
              <StatusBadge status={s.status} />
            </div>
          ))}
        </div>
      </div>

      <ChartCard
        title="CPU & RAM (current session)"
        subtitle={`${series.length} samples · 10s interval · browser-local sample`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID.stroke} vertical={false} />
            <XAxis
              dataKey="t"
              tickFormatter={(v) => `${v}s`}
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: CHART_GRID.tick }}
              tickLine={false}
              axisLine={false}
              width={32}
              domain={[0, 100]}
            />
            <Tooltip contentStyle={{ borderRadius: 12, border: `1px solid ${CHART_GRID.tooltipBorder}`, fontSize: 12 }} />
            <Line type="monotone" dataKey="cpu" stroke={CHART_PALETTE.primary} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="ram" stroke={CHART_PALETTE.secondary} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Grafana — System Health</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Postgres + Redis exporters via Prometheus.</p>
          </div>
          <a
            href={`${GRAFANA_HOST}/d/a20-system-health`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Open Grafana →
          </a>
        </div>
        <div className="overflow-hidden rounded-[20px] border border-slate-200/80 bg-white/80">
          <iframe
            src={`${GRAFANA_HOST}/d/a20-system-health?theme=light&kiosk`}
            title="Grafana — System Health"
            className="h-[640px] w-full"
            loading="lazy"
          />
        </div>
      </div>
    </div>
  );
}
