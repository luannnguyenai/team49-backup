"use client";

import Link from "next/link";
import { LogOut, Moon, Sun } from "lucide-react";

import BottomSheet from "@/components/ui/BottomSheet";
import { cn } from "@/lib/utils";
import type { NavItem } from "@/components/layout/navItems";

type MobileMenuSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  navItems: readonly NavItem[];
  pathname: string;
  isAuthenticated: boolean;
  initials: string;
  resolvedTheme?: string;
  onToggleTheme: () => void;
  onLogout: () => void | Promise<void>;
};

function isNavItemActive(pathname: string, navItem: NavItem) {
  return navItem.isActive
    ? navItem.isActive(pathname)
    : navItem.exact
      ? pathname === navItem.href
      : pathname === navItem.href || pathname.startsWith(`${navItem.href}/`);
}

export default function MobileMenuSheet({
  open,
  onOpenChange,
  navItems,
  pathname,
  isAuthenticated,
  initials,
  resolvedTheme,
  onToggleTheme,
  onLogout,
}: MobileMenuSheetProps) {
  return (
    <BottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="Menu"
      description="Jump between destinations and account actions without crowding the mobile header."
    >
      <div className="space-y-3 pt-3">
        <div className="grid gap-2">
          {navItems.map((navItem) => {
            const Icon = navItem.icon;
            const active = isNavItemActive(pathname, navItem);

            return (
              <Link
                key={navItem.href}
                href={navItem.href}
                onClick={() => onOpenChange(false)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition-colors",
                  active
                    ? "border-transparent bg-surface-accent-soft text-primary-700 dark:text-primary-300"
                    : "border-[color:var(--border-subtle)] text-text-body hover:bg-slate-50 dark:hover:bg-slate-900",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{navItem.label}</span>
              </Link>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onToggleTheme}
          className="flex w-full items-center gap-3 rounded-2xl border border-[color:var(--border-subtle)] px-4 py-3 text-left text-sm font-medium text-text-body transition-colors hover:bg-slate-50 dark:hover:bg-slate-900"
        >
          {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          <span>{resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}</span>
        </button>

        {isAuthenticated ? (
          <button
            type="button"
            onClick={() => {
              onOpenChange(false);
              void onLogout();
            }}
            className="flex w-full items-center gap-3 rounded-2xl border border-red-200 px-4 py-3 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:border-red-900/40 dark:hover:bg-red-950/40"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign out</span>
          </button>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <Link
              href="/login"
              onClick={() => onOpenChange(false)}
              className="btn-secondary justify-center px-4 py-3"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              onClick={() => onOpenChange(false)}
              className="btn-primary justify-center px-4 py-3"
            >
              Sign up
            </Link>
          </div>
        )}

        {isAuthenticated ? (
          <div className="rounded-2xl border border-[color:var(--border-subtle)] px-4 py-3 text-sm text-text-body">
            Signed in as <span className="font-semibold text-text-strong">{initials}</span>
          </div>
        ) : null}
      </div>
    </BottomSheet>
  );
}
