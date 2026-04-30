"use client";

import TopNav from "@/components/layout/TopNav";

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <TopNav />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
