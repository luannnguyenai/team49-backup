import { History, LayoutDashboard, Library, User } from "lucide-react";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/", label: "Courses", icon: Library, exact: true },
  { href: "/history", label: "Lịch sử", icon: History },
  { href: "/profile", label: "Hồ sơ", icon: User },
] as const;
