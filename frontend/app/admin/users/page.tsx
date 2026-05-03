"use client";

// app/admin/users/page.tsx — Phase 10

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ChartCard from "@/components/admin/ChartCard";
import {
  adminApi,
  type AdminUsersPage,
  type SignupPoint,
} from "@/lib/admin-api";

export default function AdminUsersPage() {
  const [data, setData] = useState<AdminUsersPage | null>(null);
  const [signups, setSignups] = useState<SignupPoint[]>([]);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminApi
      .users(page, size, debouncedQ || undefined)
      .then((r) => {
        if (!cancelled) {
          setData(r);
          setErr(null);
        }
      })
      .catch((e) => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [page, size, debouncedQ]);

  useEffect(() => {
    adminApi.signups(30).then(setSignups).catch(() => {});
  }, []);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-6">
      <ChartCard title="Signups (last 30 days)" subtitle="users.created_at" height={200}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={signups} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="usersFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} tickFormatter={(v) => String(v).slice(5)} />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={32} allowDecimals={false} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
            <Area type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={2} fill="url(#usersFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="rounded-[28px] border border-slate-200/70 bg-white/70 p-6 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Users</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Total: {data?.total ?? "—"} · Page {data?.page ?? 1} / {totalPages}
            </p>
          </div>
          <input
            value={q}
            onChange={(e) => {
              setPage(1);
              setQ(e.target.value);
            }}
            placeholder="Search email or name…"
            className="w-72 rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm shadow-sm outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-100 dark:border-slate-700 dark:bg-slate-900/60"
          />
        </div>

        {err && (
          <p className="mb-3 rounded bg-rose-50 px-3 py-2 text-xs text-rose-700">{err}</p>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Onboarded</th>
                <th className="px-3 py-2">Joined</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-slate-400">
                    Loading…
                  </td>
                </tr>
              )}
              {!loading &&
                data?.items.map((u) => (
                  <tr
                    key={u.id}
                    className="border-t border-slate-100 transition hover:bg-cyan-50/40 dark:border-slate-800 dark:hover:bg-slate-800/40"
                  >
                    <td className="px-3 py-2 font-medium text-slate-900 dark:text-white">{u.email}</td>
                    <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{u.full_name}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                          u.role === "admin"
                            ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                      {u.is_onboarded ? "✓" : "—"}
                    </td>
                    <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              {!loading && data && data.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-slate-400">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-end gap-2 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs disabled:opacity-40"
          >
            ← Prev
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
