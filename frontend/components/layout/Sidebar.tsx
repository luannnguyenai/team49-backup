"use client";
// components/layout/Sidebar.tsx
// Collapsible sidebar with nav items, logo, and user footer

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  History,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/learn", label: "Học", icon: BookOpen },
  { href: "/history", label: "Lịch sử", icon: History },
  { href: "/profile", label: "Hồ sơ", icon: User },
];

interface Props {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function Sidebar({ mobileOpen, onMobileClose }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const sidebarContent = (
    <div
      className={cn(
        "flex h-full flex-col border-r transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
      style={{
        backgroundColor: "var(--bg-sidebar)",
        borderColor: "var(--border)",
      }}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-16 items-center border-b px-4",
          collapsed ? "justify-center" : "justify-between"
        )}
        style={{ borderColor: "var(--border)" }}
      >
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 min-w-0"
          onClick={onMobileClose}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-600">
            <Brain className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <span className="truncate text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              AI Learning
            </span>
          )}
        </Link>
        {/* Collapse toggle — desktop only */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className={cn(
            "hidden lg:flex h-6 w-6 items-center justify-center rounded-md transition-colors",
            "hover:bg-slate-100 dark:hover:bg-slate-800",
            collapsed && "ml-0"
          )}
          aria-label={collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"}
          style={{ color: "var(--text-muted)" }}
        >
          {collapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronLeft className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={onMobileClose}
              className={cn(
                "sidebar-item group relative",
                active && "active",
                collapsed && "justify-center px-2"
              )}
              title={collapsed ? label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
              {/* Tooltip for collapsed mode */}
              {collapsed && (
                <div
                  className="pointer-events-none absolute left-full ml-2 z-50 hidden rounded-md
                             bg-slate-900 px-2.5 py-1.5 text-xs text-white shadow-lg group-hover:flex"
                >
                  {label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div
        className="border-t p-3"
        style={{ borderColor: "var(--border)" }}
      >
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg px-2 py-2",
            collapsed && "justify-center"
          )}
        >
          {/* Avatar */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 text-sm font-semibold">
            {user?.full_name?.[0]?.toUpperCase() ?? "?"}
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                {user?.full_name ?? "—"}
              </p>
              <p className="truncate text-xs" style={{ color: "var(--text-muted)" }}>
                {user?.email ?? "—"}
              </p>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={handleLogout}
              className="rounded-md p-1.5 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500"
              aria-label="Đăng xuất"
              style={{ color: "var(--text-muted)" }}
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
        {collapsed && (
          <button
            onClick={handleLogout}
            className="mt-1 flex w-full items-center justify-center rounded-lg p-2 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500"
            style={{ color: "var(--text-muted)" }}
            aria-label="Đăng xuất"
          >
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex h-screen sticky top-0 flex-col">
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          onClick={onMobileClose}
          aria-label="Đóng menu"
        >
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <aside
            className="absolute left-0 top-0 h-full z-50 flex animate-slide-in"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}
