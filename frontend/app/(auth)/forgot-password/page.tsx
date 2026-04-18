import { Suspense } from "react";
import type { Metadata } from "next";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export const metadata: Metadata = { title: "Quên mật khẩu" };

export default function ForgotPasswordPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Đặt lại mật khẩu
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Nhập email và mật khẩu mới để tiếp tục đăng nhập.
        </p>
      </div>
      <Suspense>
        <ForgotPasswordForm />
      </Suspense>
    </>
  );
}
