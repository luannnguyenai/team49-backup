// app/(protected)/learn/page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Học tập" };

export default function LearnPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Học tập
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Tiếp tục lộ trình học tập được cá nhân hoá.
        </p>
      </div>
      <div className="card flex min-h-64 items-center justify-center">
        <p style={{ color: "var(--text-muted)" }} className="text-sm">
          Nội dung học sẽ được tải ở đây.
        </p>
      </div>
    </div>
  );
}
