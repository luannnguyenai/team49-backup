"use client";
// components/layout/TopNav.tsx
// Horizontal top navigation bar — replaces the left Sidebar + TopBar combo.

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Brain,
  Moon,
  Sun,
  Bell,
  LogOut,
  Search,
  Menu,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { NAV_ITEMS, type NavItem } from "@/components/layout/navItems";

export default function TopNav() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { resolvedTheme, setTheme } = useTheme();
  const isAuthenticated = user !== null;

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  const isNavItemActive = (navItem: NavItem) =>
    navItem.isActive
      ? navItem.isActive(pathname)
      : navItem.exact
        ? pathname === navItem.href
        : pathname === navItem.href || pathname.startsWith(`${navItem.href}/`);

  return (
    <>
      <header
        className="sticky top-0 z-30 border-b"
        style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        <div className="flex h-16 items-center gap-4 px-4 md:px-6">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
              <Brain className="h-4 w-4 text-white" />
            </div>
            <span className="hidden sm:block text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              AI Learning Hub
            </span>
          </Link>

          {/* Desktop nav links */}
          <nav className="hidden md:flex items-center gap-1 ml-4">
            {NAV_ITEMS.map((navItem) => {
              const { href, label, icon: Icon } = navItem;
              const active = isNavItemActive(navItem);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                  style={active ? {} : { color: "var(--text-secondary)" }}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Search — center, flex-1 */}
          <div className="flex-1 max-w-xs mx-auto hidden sm:block">
            <label
              className="flex items-center gap-2 rounded-full border px-3 py-2"
              style={{ backgroundColor: "var(--bg-page)", borderColor: "var(--border)" }}
            >
              <Search className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
              <input
                aria-label="Tìm kiếm khóa học"
                placeholder="Tìm kiếm khóa học..."
                readOnly
                tabIndex={-1}
                value=""
                className="w-full bg-transparent text-sm outline-none placeholder:text-[color:var(--text-muted)]"
                style={{ color: "var(--text-primary)" }}
              />
            </label>
          </div>

          {/* Right actions */}
          <div className="ml-auto flex items-center gap-1">
            {/* Dark mode toggle */}
            <button
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
              className="flex h-9 w-9 items-center justify-center rounded-full transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Chuyển giao diện"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </button>

            {/* Notifications */}
            <button
              className="relative flex h-9 w-9 items-center justify-center rounded-full transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Thông báo"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500" aria-hidden="true" />
              <span className="sr-only">Có thông báo chưa đọc</span>
            </button>

            {isAuthenticated ? (
              <>
                {/* Avatar */}
                <Link
                  href="/profile"
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 text-sm font-semibold transition-opacity hover:opacity-80"
                >
                  {initials}
                </Link>

                {/* Logout */}
                <button
                  onClick={handleLogout}
                  className="hidden sm:flex h-9 items-center gap-1.5 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden lg:block">Đăng xuất</span>
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="hidden sm:inline-flex h-9 items-center rounded-full bg-slate-950 px-4 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                Đăng nhập
              </Link>
            )}

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen((o) => !o)}
              className="flex md:hidden h-9 w-9 items-center justify-center rounded-full transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Menu"
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div
            className="md:hidden border-t px-4 py-3 space-y-1"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-card)" }}
          >
            {NAV_ITEMS.map((navItem) => {
              const { href, label, icon: Icon } = navItem;
              const active = isNavItemActive(navItem);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                  style={active ? {} : { color: "var(--text-secondary)" }}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
            {isAuthenticated ? (
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-500"
                style={{ color: "var(--text-secondary)" }}
              >
                <LogOut className="h-4 w-4" />
                Đăng xuất
              </button>
            ) : (
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="flex w-full items-center justify-center rounded-lg bg-slate-950 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                Đăng nhập
              </Link>
            )}
          </div>
        )}
      </header>
    </>
  );
}
