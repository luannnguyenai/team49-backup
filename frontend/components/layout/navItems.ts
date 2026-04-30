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
  { href: "/learn", label: "Learn", icon: BookOpen },
  {
    href: "/",
    label: "Courses",
    icon: Library,
    isActive: (pathname) => pathname === "/" || pathname.startsWith("/courses/"),
  },
  { href: "/history", label: "History", icon: History },
  { href: "/profile", label: "Profile", icon: User },
] as const satisfies readonly NavItem[];
