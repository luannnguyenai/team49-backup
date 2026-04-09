// app/(protected)/dashboard/page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Dashboard
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Tổng quan tiến trình học tập của bạn.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { label: "Topics hoàn thành", value: "0", unit: "topics" },
          { label: "Thời gian học tuần này", value: "0", unit: "giờ" },
          { label: "Điểm mastery TB", value: "—", unit: "%" },
        ].map((stat) => (
          <div key={stat.label} className="card">
            <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              {stat.label}
            </p>
            <p className="mt-2 text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
              {stat.value}
              <span className="ml-1 text-base font-normal" style={{ color: "var(--text-muted)" }}>
                {stat.unit}
              </span>
            </p>
          </div>
        ))}
      </div>

      {/* Placeholder */}
      <div className="card flex min-h-48 items-center justify-center">
        <p style={{ color: "var(--text-muted)" }} className="text-sm">
          Lộ trình học tập sẽ hiển thị ở đây sau khi bạn hoàn thành onboarding.
        </p>
      </div>
    </div>
  );
}
