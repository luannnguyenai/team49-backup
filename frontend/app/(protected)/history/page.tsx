// app/(protected)/history/page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Lịch sử" };

export default function HistoryPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Lịch sử học tập
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Xem lại các phiên học và kết quả kiểm tra.
        </p>
      </div>
      <div className="card flex min-h-64 items-center justify-center">
        <p style={{ color: "var(--text-muted)" }} className="text-sm">
          Chưa có phiên học nào.
        </p>
      </div>
    </div>
  );
}
