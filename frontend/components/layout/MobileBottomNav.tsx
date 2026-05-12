"use client";

import Link from "next/link";

import { getMobilePrimaryNavItems, type NavItem } from "@/components/layout/navItems";
import { cn } from "@/lib/utils";

function isNavItemActive(pathname: string, navItem: NavItem) {
  return navItem.isActive
    ? navItem.isActive(pathname)
    : navItem.exact
      ? pathname === navItem.href
      : pathname === navItem.href || pathname.startsWith(`${navItem.href}/`);
}

type MobileBottomNavProps = {
  pathname: string;
};

export default function MobileBottomNav({ pathname }: MobileBottomNavProps) {
  const items = getMobilePrimaryNavItems(true);

  return (
    <nav
      aria-label="Mobile primary navigation"
      className="mobile-safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-[color:var(--border-subtle)] bg-[color:var(--glass-bg)] px-2 pt-2 backdrop-blur-xl md:hidden"
    >
      <ul className="grid grid-cols-5 gap-1">
        {items.map((navItem) => {
          const active = isNavItemActive(pathname, navItem);
          const Icon = navItem.icon;

          return (
            <li key={navItem.href}>
              <Link
                href={navItem.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-[3.25rem] flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-medium transition-colors",
                  active
                    ? "bg-surface-accent-soft text-primary-700 dark:text-primary-300"
                    : "text-text-body hover:bg-slate-100 dark:hover:bg-slate-800",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{navItem.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
