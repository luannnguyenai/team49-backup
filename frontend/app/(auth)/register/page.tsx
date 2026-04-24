// app/(auth)/register/page.tsx

import { Suspense } from "react";
import type { Metadata } from "next";
import RegisterForm from "@/components/auth/RegisterForm";

export const metadata: Metadata = { title: "Đăng ký" };

export default function RegisterPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Tạo tài khoản mới ✨
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Miễn phí. Không cần thẻ tín dụng.
        </p>
      </div>
      <Suspense>
        <RegisterForm />
      </Suspense>
    </>
  );
}
