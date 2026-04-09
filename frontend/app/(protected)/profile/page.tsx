"use client";
// app/(protected)/profile/page.tsx

import { useAuthStore } from "@/stores/authStore";
import { formatDate } from "@/lib/utils";
import { User, Mail, Clock, Calendar, BookOpen } from "lucide-react";

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);

  if (!user) return null;

  const fields = [
    {
      label: "Họ và tên",
      value: user.full_name,
      icon: <User className="h-4 w-4" />,
    },
    {
      label: "Email",
      value: user.email,
      icon: <Mail className="h-4 w-4" />,
    },
    {
      label: "Giờ học / tuần",
      value: user.available_hours_per_week
        ? `${user.available_hours_per_week} giờ`
        : "Chưa đặt",
      icon: <Clock className="h-4 w-4" />,
    },
    {
      label: "Deadline",
      value: user.target_deadline ? formatDate(user.target_deadline) : "Chưa đặt",
      icon: <Calendar className="h-4 w-4" />,
    },
    {
      label: "Phương pháp học",
      value:
        user.preferred_method === "reading"
          ? "📖 Đọc tài liệu"
          : user.preferred_method === "video"
          ? "🎥 Xem video"
          : "Chưa đặt",
      icon: <BookOpen className="h-4 w-4" />,
    },
  ];

  return (
    <div className="max-w-2xl space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Hồ sơ
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Thông tin tài khoản và cài đặt học tập.
        </p>
      </div>

      {/* Avatar section */}
      <div className="card flex items-center gap-5">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 text-2xl font-bold">
          {user.full_name[0].toUpperCase()}
        </div>
        <div>
          <p className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
            {user.full_name}
          </p>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {user.email}
          </p>
          <span
            className={`mt-1.5 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              user.is_onboarded
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
            }`}
          >
            {user.is_onboarded ? "✓ Đã onboarding" : "⏳ Chưa onboarding"}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="card divide-y" style={{ borderColor: "var(--border)" }}>
        {fields.map(({ label, value, icon }) => (
          <div key={label} className="flex items-center gap-4 py-4 first:pt-0 last:pb-0">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
              style={{
                backgroundColor: "var(--bg-page)",
                color: "var(--text-secondary)",
              }}
            >
              {icon}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                {label}
              </p>
              <p className="mt-0.5 text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
                {value}
              </p>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        Thành viên từ {formatDate(user.created_at)}
      </p>
    </div>
  );
}
