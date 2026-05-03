import { Suspense } from "react";
import type { Metadata } from "next";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export const metadata: Metadata = { title: "Forgot Password" };

export default function ForgotPasswordPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Reset your password
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          Enter your email and a new password to sign in again.
        </p>
      </div>
      <Suspense>
        <ForgotPasswordForm />
      </Suspense>
    </>
  );
}
