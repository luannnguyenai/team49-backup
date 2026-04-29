"use client";
// components/layout/TopNav.tsx
// Horizontal top navigation bar — replaces the left Sidebar + TopBar combo.

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Moon, Sun, Bell, LogOut, Search, Menu, X } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import BrandLogo from "@/components/layout/BrandLogo";
import { NAV_ITEMS, type NavItem } from "@/components/layout/navItems";
import { getCachedAllCourseCatalog } from "@/lib/course-catalog-cache";
import { filterCoursesByQuery, normalizeCourseSearchQuery } from "@/lib/course-search";
import type { CourseCatalogItem } from "@/types";

const MIN_SEARCH_QUERY_LENGTH = 2;
const MAX_DROPDOWN_RESULTS = 6;

function getCourseHref(courseSlug: string) {
  return `/courses/${courseSlug}`;
}

function TopNavSearch({ pathname }: { pathname: string }) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mountedRef = useRef(true);
  const [draftQuery, setDraftQuery] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [catalogCourses, setCatalogCourses] = useState<CourseCatalogItem[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [hasLoadedCourses, setHasLoadedCourses] = useState(false);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    setDraftQuery("");
    setIsDropdownOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, []);

  const normalizedQuery = normalizeCourseSearchQuery(draftQuery);
  const hasSearchTerm = normalizedQuery.length >= MIN_SEARCH_QUERY_LENGTH;
  const matchingCourses = hasSearchTerm
    ? filterCoursesByQuery(catalogCourses, draftQuery).slice(0, MAX_DROPDOWN_RESULTS)
    : [];
  const showDropdown = isDropdownOpen && hasSearchTerm;

  const clearQuery = () => {
    setDraftQuery("");
    setIsDropdownOpen(false);
  };

  const ensureCatalogLoaded = () => {
    if (hasLoadedCourses || isLoadingCourses) {
      return;
    }

    setIsLoadingCourses(true);
    getCachedAllCourseCatalog(true)
      .then((response) => {
        if (mountedRef.current) {
          setCatalogCourses(response.items);
          setHasLoadedCourses(true);
        }
      })
      .catch(() => {
        if (mountedRef.current) {
          setCatalogCourses([]);
          setHasLoadedCourses(false);
        }
      })
      .finally(() => {
        if (mountedRef.current) {
          setIsLoadingCourses(false);
        }
      });
  };

  const hasDraftQuery = draftQuery.length > 0;

  return (
    <div ref={containerRef} className="min-w-0 flex-1">
      <div className="relative mx-auto max-w-md">
        <label
          className="flex items-center gap-2 rounded-full border px-3 py-2"
          style={{ backgroundColor: "var(--bg-page)", borderColor: "var(--border)" }}
        >
          <Search className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
          <input
            aria-label="Tìm kiếm khóa học"
            placeholder="Tìm theo tên khóa học, mô tả..."
            value={draftQuery}
            onFocus={() => {
              setIsDropdownOpen(true);
              ensureCatalogLoaded();
            }}
            onChange={(event) => {
              setDraftQuery(event.target.value);
              setIsDropdownOpen(true);
              ensureCatalogLoaded();
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                setIsDropdownOpen(false);
              }
            }}
            className="w-full bg-transparent text-sm outline-none placeholder:text-[color:var(--text-muted)]"
            style={{ color: "var(--text-primary)" }}
          />
          {hasDraftQuery && (
            <button
              type="button"
              aria-label="Xóa từ khóa tìm kiếm"
              onClick={clearQuery}
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-colors hover:bg-slate-200 dark:hover:bg-slate-700"
              style={{ color: "var(--text-muted)" }}
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </label>
      {showDropdown && (
        <div
          data-testid="topnav-search-dropdown"
          className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-2xl border shadow-lg"
          style={{
            backgroundColor: "var(--bg-card)",
            borderColor: "var(--border)",
            boxShadow: "0 18px 50px rgba(15, 23, 42, 0.16)",
          }}
        >
          {isLoadingCourses ? (
            <div className="px-4 py-3 text-sm" style={{ color: "var(--text-muted)" }}>
              Đang tải khóa học...
            </div>
          ) : matchingCourses.length === 0 ? (
            <div className="px-4 py-3 text-sm" style={{ color: "var(--text-muted)" }}>
              Không tìm thấy khóa học phù hợp.
            </div>
          ) : (
            <ul className="py-2">
              {matchingCourses.map((course) => (
                <li key={course.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setIsDropdownOpen(false);
                      setDraftQuery("");
                      router.push(getCourseHref(course.slug));
                    }}
                    className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    <span className="min-w-0">
                      <span
                        className="block truncate text-sm font-semibold"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {course.title}
                      </span>
                      <span
                        className="mt-1 block text-xs leading-5"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        {course.short_description}
                      </span>
                    </span>
                    <span className="shrink-0 text-right">
                      {course.is_recommended && (
                        <span
                          className="mb-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
                          style={{
                            backgroundColor: "rgba(59, 130, 246, 0.12)",
                            color: "rgb(37, 99, 235)",
                          }}
                        >
                          Dành cho bạn
                        </span>
                      )}
                      <span
                        className="block text-[11px] uppercase tracking-[0.08em]"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {course.status === "coming_soon" ? "Sắp ra mắt" : "Sẵn sàng"}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      </div>
    </div>
  );
}

export default function TopNav() {
  return (
    <Suspense fallback={<TopNavFallback />}>
      <TopNavContent />
    </Suspense>
  );
}

function TopNavFallback() {
  return (
    <header
      className="sticky top-0 z-30 border-b"
      style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex h-16 items-center gap-4 px-4 md:px-6">
        <div className="shrink-0">
          <BrandLogo compact />
        </div>
        <div className="hidden flex-1 sm:block" />
      </div>
    </header>
  );
}

function TopNavContent() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { resolvedTheme, setTheme } = useTheme();
  const isAuthenticated = user !== null;

  const handleLogout = async () => {
    await logout();
    router.push("/");
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

  const visibleNavItems = isAuthenticated
    ? NAV_ITEMS.filter((navItem) => navItem.label !== "Courses")
    : NAV_ITEMS;
  const navItemsWithResolvedHref = useMemo(
    () =>
      visibleNavItems.map((navItem) => ({
        ...navItem,
        resolvedHref: navItem.href,
      })),
    [visibleNavItems],
  );

  return (
    <>
      <header
        className="sticky top-0 z-30 border-b"
        style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        <div className="flex h-16 items-center gap-4 px-4 md:px-6">
          {/* Logo */}
          <div className="shrink-0">
            <BrandLogo compact />
          </div>

          <Suspense fallback={<div className="min-w-0 flex-1" />}>
            <TopNavSearch pathname={pathname} />
          </Suspense>

          {/* Desktop nav links */}
          <nav className="ml-auto hidden items-center gap-1 md:flex">
            {navItemsWithResolvedHref.map((navItem) => {
              const { href, label, icon: Icon, resolvedHref } = navItem;
              const active = isNavItemActive(navItem);
              return (
                <Link
                  key={href}
                  href={resolvedHref}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
                      : "text-text-body hover:bg-surface-page dark:hover:bg-slate-800"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-1">
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
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300 text-sm font-semibold transition-opacity hover:opacity-80"
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
            {navItemsWithResolvedHref.map((navItem) => {
              const { href, label, icon: Icon, resolvedHref } = navItem;
              const active = isNavItemActive(navItem);
              return (
                <Link
                  key={href}
                  href={resolvedHref}
                  onClick={() => setMobileOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-surface-accent-soft text-primary-700 dark:bg-surface-accent-soft dark:text-primary-300"
                      : "text-text-body hover:bg-surface-page dark:hover:bg-slate-800"
                  )}
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
