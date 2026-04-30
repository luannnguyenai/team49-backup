"use client";

import TopNav from "@/components/layout/TopNav";

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-50">
      <TopNav />
      <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
