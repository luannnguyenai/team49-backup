import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  History,
  LayoutDashboard,
  Library,
  MessageSquareText,
  User,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  isActive?: (pathname: string) => boolean;
  mobilePriority?: number;
}

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, mobilePriority: 1 },
  { href: "/agent", label: "AI Assistant", icon: MessageSquareText, mobilePriority: 3 },
  { href: "/learn", label: "Learn", icon: BookOpen, mobilePriority: 2 },
  {
    href: "/",
    label: "Courses",
    icon: Library,
    mobilePriority: 2,
    isActive: (pathname) => pathname === "/" || pathname.startsWith("/courses/"),
  },
  { href: "/history", label: "History", icon: History, mobilePriority: 4 },
  { href: "/profile", label: "Profile", icon: User, mobilePriority: 5 },
] as const satisfies readonly NavItem[];

export function getVisibleNavItems(isAuthenticated: boolean) {
  return isAuthenticated
    ? NAV_ITEMS.filter((navItem) => navItem.label !== "Courses")
    : NAV_ITEMS;
}

export function getMobilePrimaryNavItems(isAuthenticated: boolean) {
  return getVisibleNavItems(isAuthenticated)
    .filter((navItem) => navItem.mobilePriority !== undefined)
    .sort((left, right) => (left.mobilePriority ?? Number.MAX_SAFE_INTEGER) - (right.mobilePriority ?? Number.MAX_SAFE_INTEGER));
}
