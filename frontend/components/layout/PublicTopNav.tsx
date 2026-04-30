import Link from "next/link";
import { ArrowRight } from "lucide-react";

import BrandLogo from "@/components/layout/BrandLogo";

const NAV_ITEMS = [
  { href: "#product", label: "Sản phẩm" },
  { href: "#roadmap", label: "Lộ trình học" },
  { href: "#tutor", label: "AI Assistant" },
  { href: "#contact", label: "Liên hệ" },
] as const;

export default function PublicTopNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 md:px-6">
        <BrandLogo subtitle="Guided AI skill development" />

        <nav className="ml-auto hidden items-center gap-6 md:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950 dark:text-slate-200 dark:hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 md:ml-6">
          <Link
            href="/login"
            className="inline-flex items-center rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:text-white dark:hover:border-slate-600 dark:hover:bg-slate-900"
          >
            Đăng nhập
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            Đăng ký
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
