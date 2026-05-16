"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight } from "lucide-react";

import BrandLogo from "@/components/layout/BrandLogo";
import BottomSheet from "@/components/ui/BottomSheet";

const NAV_ITEMS = [
  { href: "#product", label: "Product" },
  { href: "#roadmap", label: "Learning Path" },
  { href: "#tutor", label: "AI Assistant" },
  { href: "#contact", label: "Contact" },
] as const;

export default function PublicTopNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 md:px-6">
          <BrandLogo subtitle="Structured AI learning" />

          <nav className="ml-auto hidden items-center gap-6 md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-text-body transition-colors hover:text-text-strong"
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2 md:ml-6">
            <Link href="/register" className="btn-primary px-4 py-2">
              Sign up
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="btn-secondary px-4 py-2 md:hidden"
            >
              Menu
            </button>
            <Link href="/login" className="btn-secondary hidden px-4 py-2 md:inline-flex">
              Sign in
            </Link>
          </div>
        </div>
      </header>
      <BottomSheet
        open={mobileMenuOpen}
        onOpenChange={setMobileMenuOpen}
        title="Menu"
        description="Keep the public header focused on one primary action while secondary links stay reachable on mobile."
      >
        <div className="grid gap-2 pt-3">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className="rounded-2xl border border-[color:var(--border-subtle)] px-4 py-3 text-sm font-medium text-text-body transition-colors hover:bg-slate-50"
            >
              {item.label}
            </Link>
          ))}
          <Link
            href="/login"
            onClick={() => setMobileMenuOpen(false)}
            className="btn-secondary justify-center px-4 py-3"
          >
            Sign in
          </Link>
        </div>
      </BottomSheet>
    </>
  );
}
