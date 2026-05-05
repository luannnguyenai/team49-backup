// app/(auth)/layout.tsx
// Centered card layout for login / register pages

import type { Metadata } from "next";
import { Brain } from "lucide-react";

export const metadata: Metadata = {
  title: "Authentication",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-surface-page p-4"
    >
      {/* Decorative blobs */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary-600/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-primary-400/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Brand mark */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="hero-gradient flex h-12 w-12 items-center justify-center rounded-2xl shadow-lg shadow-primary-600/30">
            <Brain className="h-6 w-6 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-text-strong">
              AI Learning Platform
            </h1>
            <p className="mt-0.5 text-sm text-text-muted">
              Learn smarter every day
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="card-glass animate-fade-in">{children}</div>
      </div>
    </div>
  );
}
