import Link from "next/link";
import { ArrowRight } from "lucide-react";

import BrandLogo from "@/components/layout/BrandLogo";

const NAV_ITEMS = [
  { href: "#product", label: "Product" },
  { href: "#roadmap", label: "Learning Path" },
  { href: "#tutor", label: "AI Assistant" },
  { href: "#contact", label: "Contact" },
] as const;

export default function PublicTopNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 md:px-6">
        <BrandLogo subtitle="Structured AI learning" />

        <nav className="ml-auto hidden items-center gap-6 md:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-text-body transition-colors hover:text-text-strong dark:text-slate-200 dark:hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 md:ml-6">
          <Link
            href="/login"
            className="btn-secondary px-4 py-2"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="btn-primary px-4 py-2"
          >
            Sign up
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </header>
  );
}
