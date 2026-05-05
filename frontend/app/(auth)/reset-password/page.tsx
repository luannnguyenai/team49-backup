import { Suspense } from "react";
import type { Metadata } from "next";

import ResetPasswordForm from "@/components/auth/ResetPasswordForm";

export const metadata: Metadata = { title: "Reset Password" };

export default function ResetPasswordPage() {
  return (
    <>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-text-strong">
          Set a new password
        </h2>
        <p className="mt-1 text-sm text-text-body">
          Enter a new password for your account.
        </p>
      </div>
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </>
  );
}
