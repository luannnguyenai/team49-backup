"use client";

import { useEffect, useMemo, useState } from "react";

import KpiCard from "@/components/admin/KpiCard";
import KpiGroup from "@/components/admin/KpiGroup";
import { adminApi, type AdminLogEvent, type AdminLogsEventsResponse, type AdminLogsSummary } from "@/lib/admin-api";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function levelClass(level: string): string {
  if (level === "error") return "bg-rose-100 text-rose-700";
  if (level === "warn") return "bg-amber-100 text-amber-700";
  return "bg-cyan-100 text-cyan-700";
}

export default function AdminLogsPage() {
  const [summary, setSummary] = useState<AdminLogsSummary | null>(null);
  const [events, setEvents] = useState<AdminLogsEventsResponse | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AdminLogEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [summaryData, eventsData] = await Promise.all([
          adminApi.logsSummary(100),
          adminApi.logsEvents({ limit: 100 }),
        ]);
        if (cancelled) return;
        setSummary(summaryData);
        setEvents(eventsData);
        setSelectedEvent((current) => current ?? eventsData.items[0] ?? null);
        setErr(null);
      } catch (error) {
        if (!cancelled) {
          setErr(String((error as Error).message ?? error));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const sourceStates = useMemo(
    () => Object.entries(events?.sources ?? summary?.sources ?? {}),
    [events?.sources, summary?.sources],
  );

  return (
    <div className="space-y-6">
      <div className="rounded-[24px] border border-slate-200/70 bg-white/70 px-5 py-4 backdrop-blur-md">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-600">
          Observability
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900 md:text-2xl">
          Unified Log Explorer
        </h2>
        <p className="mt-1.5 text-sm text-slate-600">
          App, access, container, CloudWatch, and Loki events in one triage surface.
        </p>
      </div>

      <KpiGroup title="Volume" cols={4}>
        <KpiCard label="Events" value={summary?.totals.events ?? "—"} loading={loading} />
        <KpiCard label="Errors" value={summary?.totals.errors ?? "—"} loading={loading} />
        <KpiCard label="Warnings" value={summary?.totals.warnings ?? "—"} loading={loading} />
        <KpiCard label="Services" value={summary?.totals.services ?? "—"} loading={loading} />
      </KpiGroup>

      <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md">
        <h3 className="text-sm font-semibold text-slate-900">Sources</h3>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {sourceStates.map(([name, state]) => (
            <div
              key={name}
              className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3"
            >
              <p className="text-sm font-semibold text-slate-900">
                {name} · {state.status}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {state.count} event{state.count === 1 ? "" : "s"}
              </p>
              {state.message ? (
                <p className="mt-2 text-xs text-slate-600">{state.message}</p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {err ? (
        <p className="rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md">
          <h3 className="text-sm font-semibold text-slate-900">Recent events</h3>
          <div className="mt-4 space-y-3">
            {(events?.items ?? []).map((event) => (
              <button
                key={event.id}
                type="button"
                onClick={() => setSelectedEvent(event)}
                className="block w-full rounded-xl border border-slate-200/70 bg-white/85 px-4 py-3 text-left hover:border-cyan-300 hover:bg-cyan-50/70"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {event.message}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {event.service} · {event.source} · {formatTimestamp(event.timestamp)}
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${levelClass(event.level)}`}>
                    {event.level}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-[24px] border border-slate-200/70 bg-white/70 p-5 backdrop-blur-md">
          <h3 className="text-sm font-semibold text-slate-900">Event detail</h3>
          {selectedEvent ? (
            <div className="mt-4 space-y-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {selectedEvent.message}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {selectedEvent.service} · {selectedEvent.source} · {formatTimestamp(selectedEvent.timestamp)}
                </p>
              </div>
              <pre className="overflow-x-auto rounded-xl bg-slate-950/95 p-4 text-xs text-slate-100">
                {JSON.stringify(selectedEvent.raw, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Select an event to inspect raw details.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
