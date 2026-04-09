"use client";
// components/layout/TopBar.tsx
// Top navigation bar with page title, theme toggle, notifications, and avatar

import { useTheme } from "next-themes";
import { useAuthStore } from "@/stores/authStore";
import { Menu, Sun, Moon, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  title?: string;
  onMenuClick: () => void;
}

export default function TopBar({ title, onMenuClick }: Props) {
  const { theme, setTheme } = useTheme();
  const user = useAuthStore((s) => s.user);

  const toggleTheme = () =>
    setTheme(theme === "dark" ? "light" : "dark");

  return (
    <header
      className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b px-4 md:px-6"
      style={{
        backgroundColor: "var(--bg-card)",
        borderColor: "var(--border)",
      }}
    >
      {/* Mobile hamburger */}
      <button
        onClick={onMenuClick}
        className="btn-ghost lg:hidden"
        aria-label="Mở menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Page title */}
      <div className="flex-1 min-w-0">
        {title && (
          <h1
            className="truncate text-base font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {title}
          </h1>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1.5">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="btn-ghost h-9 w-9 p-0"
          aria-label="Đổi giao diện"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        {/* Notifications */}
        <button
          className="btn-ghost relative h-9 w-9 p-0"
          aria-label="Thông báo"
        >
          <Bell className="h-4 w-4" />
          {/* Badge */}
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary-600" />
        </button>

        {/* User avatar */}
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full",
            "bg-primary-100 dark:bg-primary-900/30 text-primary-600",
            "text-sm font-semibold cursor-pointer hover:ring-2 hover:ring-primary-300 transition-all"
          )}
          aria-label="Hồ sơ"
          title={user?.full_name}
        >
          {user?.full_name?.[0]?.toUpperCase() ?? "?"}
        </div>
      </div>
    </header>
  );
}
