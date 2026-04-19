"use client";

import TopNav from "@/components/layout/TopNav";

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen" style={{ backgroundColor: "var(--bg-page)" }}>
      <TopNav />
      <main className="flex-1 p-4 md:p-6">
        {children}
      </main>
    </div>
  );
}
