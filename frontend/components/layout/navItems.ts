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
}

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/tutor", label: "AI Tutor", icon: MessageSquareText },
  { href: "/learn", label: "Học", icon: BookOpen },
  {
    href: "/",
    label: "Courses",
    icon: Library,
    isActive: (pathname) => pathname === "/" || pathname.startsWith("/courses/"),
  },
  { href: "/history", label: "Lịch sử", icon: History },
  { href: "/profile", label: "Hồ sơ", icon: User },
] as const satisfies readonly NavItem[];
