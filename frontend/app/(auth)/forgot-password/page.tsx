import { Suspense } from "react";
import type { Metadata } from "next";

import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export const metadata: Metadata = { title: "Forgot Password" };

export default function ForgotPasswordPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-strong">
          Forgot your password?
        </h2>
        <p className="mt-1 text-sm text-text-body">
          Enter your email and we will send you a reset link.
        </p>
      </div>
      <Suspense>
        <ForgotPasswordForm />
      </Suspense>
    </>
  );
}
