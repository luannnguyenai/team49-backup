// app/(auth)/login/page.tsx

import { Suspense } from "react";
import type { Metadata } from "next";
import LoginForm from "@/components/auth/LoginForm";

export const metadata: Metadata = { title: "Đăng nhập" };

export default function LoginPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Chào mừng trở lại 👋
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Đăng nhập để tiếp tục hành trình học tập của bạn.
        </p>
      </div>
      <Suspense>
        <LoginForm />
      </Suspense>
    </>
  );
}
